"""REST API endpoints for stream management.

This module provides FastAPI routes for managing RTSP streams, including:
- CRUD operations (create, read, update, delete streams)
- Stream control (start/stop FFmpeg processing)
- MJPEG streaming endpoint for web viewing (full resolution, 5 FPS)
- Real-time detection score streaming via SSE

Key features:
- Auto-validation of RTSP URLs and FFmpeg parameters
- Hardware acceleration support (CUDA/NVDEC)
- Concurrent stream limit enforcement
- Full-resolution MJPEG output (no forced resizing)
- Graceful error handling and logging

Updated: Removed forced frame resizing to preserve original stream resolution.
This allows the frontend to display full-quality video at native resolution.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Final

import cv2
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse, Response

from ..models.stream import NewStream, EditStream, ReorderRequest
from ..services.streams_service import StreamsService
from ..utils.rtsp import validate_rtsp_url, build_ffmpeg_command
from ..utils.strings import mask_rtsp_credentials
from ..config_io import get_gpu_backend

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streams"])

# ============================================================================
# Constants
# ============================================================================

MAX_CONCURRENT_STREAMS: Final[int] = 4
"""Maximum number of streams that can be actively processed simultaneously."""

MJPEG_QUALITY: Final[int] = 85
"""JPEG encoding quality (0-100). Higher = better quality but larger size.
85 provides excellent quality for local network streaming."""

SSE_FPS: Final[int] = 5
"""Server-sent events frame rate for detection score streaming."""

# Global lock for concurrent stream starts
_start_lock = asyncio.Lock()


# ============================================================================
# Dependencies
# ============================================================================

def get_streams_service() -> StreamsService:
    """Dependency injection for streams service.
    
    Returns:
        StreamsService instance for handling stream operations.
    """
    return StreamsService()


# ============================================================================
# Helper Functions
# ============================================================================

async def validate_stream_config(
    rtsp_url: str,
    ffmpeg_params: list[str] | None,
    hw_accel_enabled: bool
) -> None:
    """Validate stream configuration before creation/update.
    
    Validates RTSP URL format, FFmpeg parameters, and hardware acceleration
    compatibility. Raises ValueError if any validation fails.
    
    Args:
        rtsp_url: RTSP URL to validate
        ffmpeg_params: Optional FFmpeg parameters to validate
        hw_accel_enabled: Whether hardware acceleration is enabled
        
    Raises:
        ValueError: If validation fails with descriptive error message
    """
    gpu_backend = get_gpu_backend()
    params = ffmpeg_params or []
    
    if not validate_rtsp_url(rtsp_url, params, gpu_backend):
        raise ValueError("Invalid RTSP URL or FFmpeg parameters")
    
    # Build command to verify compatibility
    build_ffmpeg_command(
        rtsp_url=rtsp_url,
        ffmpeg_params=params,
        target_fps=5,
        gpu_backend=gpu_backend if hw_accel_enabled else None
    )


def mask_stream_response(stream: dict) -> dict:
    """Mask RTSP credentials in stream response for security.
    
    Replaces username/password in RTSP URLs with asterisks before
    sending response to client.
    
    Args:
        stream: Stream dict containing rtsp_url
        
    Returns:
        Stream dict with masked credentials
    """
    masked = stream.copy()
    if "rtsp_url" in masked:
        masked["rtsp_url"] = mask_rtsp_credentials(masked["rtsp_url"])
    return masked


def encode_frame_to_jpeg(frame) -> bytes | None:
    """Encode OpenCV frame to JPEG bytes at original resolution.
    
    Encodes frame without resizing to preserve full quality. Uses high quality
    JPEG encoding (85%) suitable for local network streaming.
    
    Args:
        frame: OpenCV frame (numpy array) to encode
        
    Returns:
        JPEG bytes if encoding successful, None otherwise
        
    Note:
        This is a blocking operation and should be called via asyncio.to_thread()
        to avoid blocking the event loop.
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
    
    Returns GPU backend type detected on system (cuda, none, etc.)
    for hardware acceleration status.
    
    Returns:
        Dict with gpu_backend key
        
    Example:
        {"gpu_backend": "cuda"}
    """
    backend = get_gpu_backend()
    return {"gpu_backend": backend}


@router.post("/reorder")
async def reorder_streams(
    reorder_data: ReorderRequest,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Reorder streams in the dashboard.
    
    Updates the display order of streams based on provided ID array.
    
    Args:
        reorder_data: Request containing ordered array of stream IDs
        service: Injected StreamsService instance
        
    Returns:
        Success status and message
        
    Raises:
        HTTPException: 400 if order array is invalid, 500 on server error
    """
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
    """List all configured streams with masked credentials.
    
    Returns all streams in display order with RTSP credentials masked
    for security.
    
    Args:
        service: Injected StreamsService instance
        
    Returns:
        List of stream dicts sorted by order
        
    Raises:
        HTTPException: 500 on server error
    """
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
    
    Creates a new stream configuration, validates RTSP URL and parameters,
    and optionally auto-starts the stream if auto_start is enabled.
    
    Args:
        new_stream: Stream creation request with all required fields
        service: Injected StreamsService instance
        
    Returns:
        Created stream dict with masked credentials
        
    Raises:
        HTTPException: 400 on validation error, 500 on server error
    """
    try:
        # Validate configuration
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
            target_fps=new_stream.target_fps,
            auto_start=new_stream.auto_start
        )
        
        return mask_stream_response(stream)
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
    """Get a single stream by ID.
    
    Args:
        stream_id: UUID of stream to retrieve
        service: Injected StreamsService instance
        
    Returns:
        Stream dict with masked credentials
        
    Raises:
        HTTPException: 404 if stream not found, 500 on server error
    """
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
    
    Supports both PATCH and PUT methods. Only updates fields that are
    explicitly provided in the request.
    
    Args:
        stream_id: UUID of stream to update
        edit_stream: Update request with optional fields
        service: Injected StreamsService instance
        
    Returns:
        Updated stream dict with masked credentials
        
    Raises:
        HTTPException: 400 on validation error, 404 if not found, 500 on server error
    """
    try:
        # Get current stream
        current_stream = await service.get_stream(stream_id)
        if not current_stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream {stream_id} not found"
            )
        
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
            target_fps=edit_stream.target_fps,
            auto_start=edit_stream.auto_start
        )
        
        if not updated_stream:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream {stream_id} not found"
            )
        
        return mask_stream_response(updated_stream)
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
    """Delete a stream and stop it if running.
    
    Stops the stream's FFmpeg process if active, then removes the
    stream configuration.
    
    Args:
        stream_id: UUID of stream to delete
        service: Injected StreamsService instance
        
    Raises:
        HTTPException: 404 if stream not found, 500 on server error
    """
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
    """Start FFmpeg stream processing.
    
    Starts FFmpeg process to decode RTSP stream and make frames available
    for MJPEG streaming and person detection.
    
    Args:
        stream_id: UUID of stream to start
        service: Injected StreamsService instance
        
    Returns:
        Status message and current stream status
        
    Raises:
        HTTPException: 404 if not found, 409 if concurrent limit reached,
                      503 if start fails, 500 on server error
    """
    try:
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
        
        return {"message": "Stream started successfully", "status": "running"}
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
    """Stop FFmpeg stream processing.
    
    Terminates the FFmpeg process and releases resources.
    
    Args:
        stream_id: UUID of stream to stop
        service: Injected StreamsService instance
        
    Returns:
        Status message and current stream status
        
    Raises:
        HTTPException: 404 if not found, 500 on error
    """
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
    """Stream MJPEG video at full resolution for web viewing.
    
    Provides multipart MJPEG stream at original resolution (no resizing).
    Each frame is JPEG-encoded at 85% quality. Frame rate matches the
    stream's configured target_fps (typically 5 FPS).
    
    This endpoint is designed for local network use where bandwidth is
    sufficient for full-resolution streaming.
    
    Args:
        stream_id: UUID of stream to view
        service: Injected StreamsService instance
        
    Returns:
        StreamingResponse with multipart MJPEG content
        
    Raises:
        HTTPException: 404 if not found, 400 if stream not running
        
    Note:
        Stream must be started before accessing this endpoint.
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
            detail="Stream must be started before viewing. Use POST /{stream_id}/start first."
        )
    
    fps = stream.get("target_fps", 5)
    
    async def generate_frames():
        """Generate MJPEG frame stream with proper timing."""
        try:
            frame_interval = 1.0 / fps
            last_frame_time = 0
            
            while True:
                current_time = asyncio.get_event_loop().time()
                
                # Throttle frame rate to prevent overwhelming client
                if last_frame_time > 0:
                    elapsed = current_time - last_frame_time
                    if elapsed < frame_interval:
                        await asyncio.sleep(frame_interval - elapsed)
                
                frame_data = await service.get_frame(stream_id)
                if frame_data is None:
                    break
                
                ret, frame = frame_data
                if not ret or frame is None:
                    break
                
                # Encode frame at original resolution in thread pool
                jpeg_bytes = await asyncio.to_thread(encode_frame_to_jpeg, frame)
                if jpeg_bytes is None:
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


@router.get("/{stream_id}/scores")
async def stream_scores_sse(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> StreamingResponse:
    """SSE endpoint for real-time detection scores.
    
    Provides Server-Sent Events stream with person detection scores
    and bounding box coordinates. Currently returns placeholder data;
    will be replaced with actual YOLO detection results.
    
    Args:
        stream_id: UUID of stream to monitor
        service: Injected StreamsService instance
        
    Returns:
        StreamingResponse with text/event-stream content
        
    Raises:
        HTTPException: 404 if not found, 400 if not running
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
                score = {
                    "distance": random.uniform(0, 1),
                    "coordinates": {"x": random.uniform(0, 1), "y": random.uniform(0, 1)},
                    "size": random.randint(50, 200),
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