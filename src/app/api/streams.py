"""REST API endpoints for stream management.

This module provides FastAPI routes for managing RTSP streams with GPU acceleration.

Updated for GPU-only architecture:
- Enforces GPU backend detection from entrypoint.sh
- No CPU fallback (fail-fast)
- Uses singleton StreamsService from main.py (CRITICAL FIX)
- Adds snapshot endpoint for dashboard thumbnails
- 5fps MJPEG streaming at full resolution
- Constitution-compliant security and observability
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import io
from datetime import datetime, timezone
from typing import Final

import cv2
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse, Response
from PIL import Image

from ..models.stream import NewStream, EditStream, ReorderRequest
from ..services.streams_service import StreamsService
from ..utils.rtsp import validate_rtsp_url, build_ffmpeg_command
from ..utils.strings import mask_rtsp_credentials
from ..config_io import get_gpu_backend

# ============================================================================
# CRITICAL FIX: Import singleton service getter from main.py
# ============================================================================
# This ensures ALL requests use the SAME StreamsService instance with the
# SAME active_processes dict. Without this, each request creates a new
# service with an empty dict, causing "Stream not in active_processes" errors.
from ..main import get_streams_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streams"])

# ============================================================================
# Constants
# ============================================================================

MAX_CONCURRENT_STREAMS: Final[int] = 4
"""Maximum number of streams that can be actively processed simultaneously."""

MJPEG_QUALITY: Final[int] = 85
"""JPEG encoding quality (0-100). Higher = better quality but larger size."""

SSE_FPS: Final[int] = 5
"""Server-sent events frame rate for detection score streaming."""

SNAPSHOT_TIMEOUT: Final[float] = 2.0
"""Timeout in seconds for capturing snapshot frame."""

# Global lock for concurrent stream starts
_start_lock = asyncio.Lock()


# ============================================================================
# Dependencies
# ============================================================================
# 
# NOTE: The get_streams_service dependency is now imported from main.py
# It returns the singleton StreamsService instance created at startup.
# DO NOT define a new get_streams_service() function here!


# ============================================================================
# Helper Functions
# ============================================================================

async def validate_stream_config(
    rtsp_url: str,
    ffmpeg_params: list[str] | None,
    hw_accel_enabled: bool
) -> None:
    """Validate stream configuration before creation/update.
    
    Constitution-compliant validation:
    - GPU backend MUST be detected (no CPU fallback)
    - FFmpeg params validated for shell injection
    - RTSP URL format validated
    
    Args:
        rtsp_url: RTSP URL to validate
        ffmpeg_params: Optional FFmpeg parameters to validate
        hw_accel_enabled: Whether hardware acceleration is enabled
        
    Raises:
        ValueError: If validation fails with descriptive error message
        RuntimeError: If GPU required but not detected
    """
    gpu_backend = get_gpu_backend()
    params = ffmpeg_params or []
    
    # Constitution Principle III: GPU backend contract
    if gpu_backend == "none":
        raise RuntimeError(
            "GPU backend not detected. This application requires GPU acceleration. "
            "Ensure NVIDIA/AMD/Intel GPU with drivers is available."
        )
    
    if not validate_rtsp_url(rtsp_url, params, gpu_backend):
        raise ValueError("Invalid RTSP URL or FFmpeg parameters")
    
    # Build command to verify compatibility
    build_ffmpeg_command(
        rtsp_url=rtsp_url,
        ffmpeg_params=params,
        gpu_backend=gpu_backend
    )


def mask_stream_response(stream: dict) -> dict:
    """Mask RTSP credentials in stream response for security."""
    masked = stream.copy()
    if "rtsp_url" in masked:
        masked["rtsp_url"] = mask_rtsp_credentials(masked["rtsp_url"])
    return masked


def encode_frame_to_jpeg(frame) -> bytes | None:
    """Encode OpenCV frame to JPEG bytes at original resolution.
    
    Full-resolution encoding as per constitution requirements.
    """
    try:
        ret, jpeg = cv2.imencode(
            '.jpg', 
            frame, 
            [cv2.IMWRITE_JPEG_QUALITY, MJPEG_QUALITY]
        )
        if not ret:
            return None
        
        return jpeg.tobytes()
    except Exception as e:
        logger.error(f"Error encoding frame: {e}")
        return None


# ============================================================================
# Utility Endpoints (MUST BE BEFORE /{stream_id} ROUTES)
# ============================================================================

@router.get("/gpu-backend")
async def get_gpu_info() -> dict:
    """Get detected GPU backend information.
    
    Returns GPU backend detected by entrypoint.sh via GPU_BACKEND_DETECTED env var.
    Constitution Principle III: Explicit GPU backend contract.
    
    Returns:
        Dict with gpu_backend key (nvidia, amd, intel, or none)
    """
    backend = get_gpu_backend()
    
    if backend == "none":
        logger.warning("GPU backend not detected - application requires GPU")
    
    return {
        "gpu_backend": backend,
        "gpu_required": True,
        "message": f"GPU backend: {backend}" if backend != "none" else "No GPU detected - application will fail to start streams"
    }


@router.post("/reorder")
async def reorder_streams(
    reorder_data: ReorderRequest,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Reorder streams in the dashboard."""
    try:
        success = await service.reorder_streams(reorder_data.order)
        return {"success": success, "message": "Streams reordered successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error reordering streams: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder streams"
        )


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("")
async def list_streams(
    service: StreamsService = Depends(get_streams_service)
) -> list[dict]:
    """List all configured streams with masked credentials."""
    try:
        streams = await service.list_streams()
        return [mask_stream_response(stream) for stream in streams]
    except Exception as e:
        logger.error(f"Error listing streams: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list streams"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_stream(
    new_stream: NewStream,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Create a new stream with validation and auto-start support.
    
    Constitution Principle III: GPU backend validation on creation.
    """
    try:
        # Validate configuration (includes GPU check)
        await validate_stream_config(
            rtsp_url=new_stream.rtsp_url,
            ffmpeg_params=new_stream.ffmpeg_params,
            hw_accel_enabled=new_stream.hw_accel_enabled
        )
        
        # Create stream with auto_start support
        stream = await service.create_stream(
            name=new_stream.name,
            rtsp_url=new_stream.rtsp_url,
            hw_accel_enabled=new_stream.hw_accel_enabled,
            ffmpeg_params=new_stream.ffmpeg_params,
            auto_start=new_stream.auto_start
        )
        
        return mask_stream_response(stream)
    except RuntimeError as e:
        # GPU detection failures
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating stream: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create stream"
        )


@router.get("/{stream_id}")
async def get_stream(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Get a single stream by ID."""
    try:
        stream = await service.get_stream(stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream {stream_id} not found"
            )
        return mask_stream_response(stream)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stream"
        )
    

@router.patch("/{stream_id}")
@router.put("/{stream_id}")
async def update_stream(
    stream_id: str,
    edit_stream: EditStream,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Update an existing stream (partial update).
    
    Auto-restarts stream if FFmpeg params or RTSP URL changes while running.
    """
    try:
        # Get current stream
        current_stream = await service.get_stream(stream_id)
        if not current_stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream {stream_id} not found"
            )
        
        # Track if restart needed
        needs_restart = False
        was_running = current_stream["status"] == "running"
        
        # Check if critical params changed
        if was_running:
            if edit_stream.rtsp_url and edit_stream.rtsp_url != current_stream["rtsp_url"]:
                needs_restart = True
                logger.info(f"RTSP URL changed for {stream_id}, will restart")
            
            if edit_stream.ffmpeg_params is not None:
                current_params = set(current_stream.get("ffmpeg_params", []))
                new_params = set(edit_stream.ffmpeg_params)
                if current_params != new_params:
                    needs_restart = True
                    logger.info(f"FFmpeg params changed for {stream_id}, will restart")
            
            if edit_stream.hw_accel_enabled is not None:
                if edit_stream.hw_accel_enabled != current_stream.get("hw_accel_enabled"):
                    needs_restart = True
                    logger.info(f"Hardware acceleration changed for {stream_id}, will restart")
        
        # Stop stream if restart needed
        if needs_restart:
            logger.info(f"Stopping stream {stream_id} for parameter update")
            await service.stop_stream(stream_id)
        
        # Re-validate if URL or params changed
        if edit_stream.rtsp_url is not None or edit_stream.ffmpeg_params is not None:
            url = edit_stream.rtsp_url or current_stream["rtsp_url"]
            params = edit_stream.ffmpeg_params or current_stream.get("ffmpeg_params", [])
            hw_accel = (
                edit_stream.hw_accel_enabled 
                if edit_stream.hw_accel_enabled is not None 
                else current_stream.get("hw_accel_enabled", False)
            )
            
            await validate_stream_config(url, params, hw_accel)
        
        # Update stream
        updated_stream = await service.update_stream(
            stream_id=stream_id,
            name=edit_stream.name,
            rtsp_url=edit_stream.rtsp_url,
            status=edit_stream.status,
            hw_accel_enabled=edit_stream.hw_accel_enabled,
            ffmpeg_params=edit_stream.ffmpeg_params,
            auto_start=edit_stream.auto_start
        )
        
        if not updated_stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream {stream_id} not found"
            )
        
        # Restart stream if it was running and params changed
        if needs_restart:
            logger.info(f"Restarting stream {stream_id} with new parameters")
            success = await service.start_stream(stream_id, updated_stream)
            if not success:
                logger.error(f"Failed to restart stream {stream_id}")
                # Don't fail the update, just log the error
        
        return mask_stream_response(updated_stream)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update stream"
        )


@router.delete("/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stream(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> None:
    """Delete a stream and stop it if running."""
    try:
        deleted = await service.delete_stream(stream_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream {stream_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete stream"
        )


# ============================================================================
# Stream Control Endpoints
# ============================================================================

@router.post("/{stream_id}/start")
async def start_stream(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Start FFmpeg stream processing with GPU acceleration.
    
    Constitution Principle III: Fail-fast if GPU not available.
    """
    try:
        # Check GPU backend
        gpu_backend = get_gpu_backend()
        if gpu_backend == "none":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GPU backend not detected. Cannot start stream."
            )
        
        stream = await service.get_stream(stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stream not found"
            )
        
        if stream["status"] == "running":
            return {"message": "Stream already running", "status": "running"}
        
        async with _start_lock:
            if len(service.active_processes) >= MAX_CONCURRENT_STREAMS:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Maximum concurrent streams ({MAX_CONCURRENT_STREAMS}) reached"
                )
            
            success = await service.start_stream(stream_id, stream)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to start stream processing"
                )
        
        return {"message": "Stream started successfully", "status": "running", "gpu_backend": gpu_backend}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start stream"
        )


@router.post("/{stream_id}/stop")
async def stop_stream(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Stop FFmpeg stream processing."""
    try:
        stream = await service.get_stream(stream_id)
        if not stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stream not found"
            )
        
        if stream["status"] != "running":
            return {"message": "Stream not running", "status": "stopped"}
        
        success = await service.stop_stream(stream_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop stream"
            )
        
        return {"message": "Stream stopped successfully", "status": "stopped"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop stream"
        )


# ============================================================================
# Streaming Endpoints
# ============================================================================

@router.get("/{stream_id}/mjpeg")
async def stream_mjpeg(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> StreamingResponse:
    """Stream MJPEG video at full resolution (5fps) for web viewing.
    
    Constitution Principle II: 5 FPS cap, full resolution, no video storage.
    """
    stream = await service.get_stream(stream_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found"
        )
    
    if stream["status"] != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream must be started before viewing."
        )
    
    fps = stream.get("target_fps", 5)
    
    async def generate_frames():
        """Generate MJPEG frame stream with proper timing."""
        try:
            frame_interval = 1.0 / fps
            last_frame_time = 0
            
            while True:
                current_time = asyncio.get_event_loop().time()
                
                # Throttle frame rate
                if last_frame_time > 0:
                    elapsed = current_time - last_frame_time
                    if elapsed < frame_interval:
                        await asyncio.sleep(frame_interval - elapsed)
                
                frame_data = await service.get_frame(stream_id)
                if frame_data is None:
                    logger.warning(f"Stream {stream_id} ended")
                    break
                
                success, jpeg_bytes = frame_data
                if not success or not jpeg_bytes:
                    # No frame ready yet, wait a bit
                    await asyncio.sleep(0.1)
                    continue
                
                # Yield MJPEG multipart frame
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n'
                    b'Content-Length: ' + str(len(jpeg_bytes)).encode() + b'\r\n\r\n' +
                    jpeg_bytes + b'\r\n'
                )
                
                last_frame_time = asyncio.get_event_loop().time()
                
        except asyncio.CancelledError:
            logger.info(f"MJPEG stream cancelled for {stream_id}")
            raise
        except Exception as e:
            logger.error(f"Error in MJPEG stream {stream_id}: {e}", exc_info=True)
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close"
        }
    )


@router.get("/{stream_id}/snapshot")
async def get_snapshot(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> Response:
    """Get a single JPEG snapshot from the stream for dashboard thumbnails.
    
    Constitution Principle II: No video storage beyond live frames.
    Returns current frame at full resolution.
    
    Args:
        stream_id: UUID of stream to snapshot
        service: Injected StreamsService instance
        
    Returns:
        JPEG image response
        
    Raises:
        HTTPException: 404 if not found, 400 if not running, 503 if frame unavailable
    """
    logger.info(f"📸 Snapshot request received for stream {stream_id}")
    
    stream = await service.get_stream(stream_id)
    if not stream:
        logger.warning(f"❌ Snapshot failed: Stream {stream_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found"
        )
    
    logger.debug(f"Stream {stream_id} status: {stream['status']}")
    logger.debug(f"Active processes: {list(service.active_processes.keys())}")
    
    if stream["status"] != "running":
        logger.warning(f"❌ Snapshot failed: Stream {stream_id} not running (status: {stream['status']})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream not running. Start stream first."
        )
    
    try:
        # Get single frame with timeout - retry up to 3 times
        max_retries = 3
        jpeg_bytes = None
        
        for attempt in range(max_retries):
            logger.debug(f"Snapshot attempt {attempt + 1}/{max_retries} for stream {stream_id}")
            
            frame_data = await asyncio.wait_for(
                service.get_frame(stream_id),
                timeout=SNAPSHOT_TIMEOUT
            )
            
            if frame_data is None:
                logger.warning(f"Attempt {attempt + 1}: get_frame returned None")
                continue
            
            success, frame_bytes = frame_data
            if success and frame_bytes:
                jpeg_bytes = frame_bytes
                logger.info(f"✅ Snapshot captured for {stream_id}: {len(jpeg_bytes)} bytes (attempt {attempt + 1})")
                break
            else:
                logger.debug(f"Attempt {attempt + 1}: success={success}, bytes_len={len(frame_bytes) if frame_bytes else 0}")
            
            # Wait a bit before retry
            await asyncio.sleep(0.2)
        
        if not jpeg_bytes:
            logger.error(f"❌ Snapshot failed for {stream_id}: No frame captured after {max_retries} retries")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to capture frame after retries"
            )
        
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "no-cache, max-age=0",
                "Pragma": "no-cache"
            }
        )
        
    except asyncio.TimeoutError:
        logger.error(f"❌ Snapshot timeout for {stream_id}: Stream may be stalled")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Snapshot timeout - stream may be stalled"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Snapshot error for {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to capture snapshot"
        )


@router.get("/{stream_id}/scores")
async def stream_scores_sse(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> StreamingResponse:
    """SSE endpoint for real-time detection scores.
    
    Constitution Principle VII: Real-time scoring for home automation.
    Currently returns placeholder data until YOLO + Shapely integration.
    
    TODO: Replace with actual YOLO person detection + polygon zone scoring.
    """
    stream = await service.get_stream(stream_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found"
        )
    
    if stream["status"] != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream not running"
        )
    
    async def event_generator():
        """Generate SSE events with detection scores."""
        try:
            while True:
                frame_data = await service.get_frame(stream_id)
                if frame_data is None:
                    break
                
                ret, frame = frame_data
                if not ret or frame is None:
                    break
                
                # TODO: Replace with actual YOLO + Shapely detection
                # Constitution Principle VII: distance, coordinates, size scoring
                score = {
                    "stream_id": stream_id,
                    "zone_id": None,  # TODO: Add zone detection
                    "object_class": "person",  # TODO: From YOLO
                    "confidence": random.uniform(0.7, 0.99),
                    "distance": random.uniform(0, 1),  # TODO: Calculate from target point
                    "coordinates": {"x": random.uniform(0, 1), "y": random.uniform(0, 1)},
                    "size": random.randint(50, 200),  # TODO: bbox width * height
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                yield f"data: {json.dumps(score)}\n\n"
                await asyncio.sleep(1 / SSE_FPS)
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for {stream_id}")
            raise
        except Exception as e:
            logger.error(f"Error in SSE stream {stream_id}: {e}", exc_info=True)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
