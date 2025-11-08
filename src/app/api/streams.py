"""REST API endpoints for stream management.

This module provides FastAPI routes for managing RTSP streams with GPU acceleration.

Architecture:
- GPU-only operation (fail-fast if GPU unavailable)
- Singleton StreamsService ensures shared FFmpeg process state
- FFmpeg outputs MJPEG at 5fps (constitution-mandated cap)
- Full resolution preservation, no video storage

Logging Strategy:
    DEBUG - Validation, state checks, retry attempts
    INFO  - Stream lifecycle (create/start/stop/delete), captures
    WARN  - Invalid configs, GPU unavailable, not found
    ERROR - Exceptions with stack traces

Constitution Compliance:
    - 5fps cap enforced (no variable fps)
    - GPU-only (no CPU fallback)
    - Full resolution (no downscaling)
    - No video storage (live frames only)
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Final

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse, Response

from ..models.stream import NewStream, EditStream, ReorderRequest
from ..services.streams_service import StreamsService
from ..utils.rtsp import validate_rtsp_url
from ..utils.strings import mask_rtsp_credentials
from ..config_io import get_gpu_backend
from ..config.ffmpeg_defaults import (
    BASE_FFMPEG_PARAMS,
    GPU_FFMPEG_PARAMS,
    get_default_ffmpeg_params_string
)
from ..services.container import get_streams_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streams"])

# ============================================================================
# T066: Rate Limiting for Motion Metrics Endpoints
# ============================================================================

import time
from collections import defaultdict, deque
from fastapi import Request

class SimpleRateLimiter:
    """Simple in-memory rate limiter using sliding window."""

    def __init__(self, max_requests: int = 10, window_seconds: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Window size in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Store timestamps per stream_id
        self._request_log: dict[str, deque] = defaultdict(lambda: deque())

    def check_rate_limit(self, stream_id: str) -> bool:
        """
        Check if request should be allowed based on rate limit.

        Args:
            stream_id: Stream identifier to rate limit

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Get request log for this stream
        log = self._request_log[stream_id]

        # Remove timestamps outside the window
        while log and log[0] < window_start:
            log.popleft()

        # Check if limit exceeded
        if len(log) >= self.max_requests:
            return False

        # Add current request timestamp
        log.append(now)
        return True

# Create global rate limiter instance (10 requests/second per stream)
motion_metrics_limiter = SimpleRateLimiter(max_requests=10, window_seconds=1.0)

# ============================================================================
# Constants
# ============================================================================

MAX_CONCURRENT_STREAMS: Final[int] = 4
"""Maximum concurrent FFmpeg processes."""

MJPEG_QUALITY: Final[int] = 85
"""JPEG encoding quality (0-100) for FFmpeg output."""

FPS: Final[int] = 5
"""Locked frame rate (constitution-mandated)."""

SNAPSHOT_TIMEOUT: Final[float] = 2.0
"""Snapshot capture timeout in seconds."""

SNAPSHOT_MAX_RETRIES: Final[int] = 3
"""Maximum snapshot retry attempts."""

# Global lock for concurrent stream starts
_start_lock = asyncio.Lock()

# ============================================================================
# Helper Functions
# ============================================================================

async def validate_stream_config(
    rtsp_url: str,
    ffmpeg_params: list[str] | None
) -> None:
    """Validate stream configuration before creation/update.
    
    Validates:
    - GPU backend availability (constitution requirement)
    - RTSP URL format
    - FFmpeg parameters (shell injection protection)
    
    Raises:
        ValueError: Invalid configuration
        RuntimeError: GPU not available
    """
    logger.debug(f"Validating config: rtsp={mask_rtsp_credentials(rtsp_url)}")
    
    gpu_backend = get_gpu_backend()
    params = ffmpeg_params or []
    
    if gpu_backend == "none":
        logger.warning("GPU backend not detected during validation")
        raise RuntimeError(
            "GPU backend not detected. This application requires GPU acceleration."
        )
    
    logger.debug(f"GPU backend: {gpu_backend}")
    
    if not validate_rtsp_url(rtsp_url, params, gpu_backend):
        logger.error(f"RTSP validation failed: {mask_rtsp_credentials(rtsp_url)}")
        raise ValueError("Invalid RTSP URL or FFmpeg parameters")
    
    logger.debug(f"Config validated: RTSP format OK, {len(params)} custom params")


def mask_stream_response(stream: dict) -> dict:
    """Mask RTSP credentials in response for security."""
    masked = stream.copy()
    if "rtsp_url" in masked:
        masked["rtsp_url"] = mask_rtsp_credentials(masked["rtsp_url"])
    return masked


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/gpu-backend")
async def get_gpu_info() -> dict:
    """Get detected GPU backend information."""
    backend = get_gpu_backend()
    logger.info(f"GPU backend query: {backend}")
    
    if backend == "none":
        logger.warning("GPU backend unavailable")
        return {
            "gpu_backend": backend,
            "gpu_required": True,
            "message": "No GPU detected - streams will fail to start"
        }
    
    return {
        "gpu_backend": backend,
        "gpu_required": True,
        "message": f"GPU backend: {backend}"
    }


@router.post("/reorder")
async def reorder_streams(
    reorder_data: ReorderRequest,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Reorder streams for dashboard display."""
    try:
        logger.info(f"Reordering {len(reorder_data.order)} stream(s)")
        success = await service.reorder_streams(reorder_data.order)
        logger.info("Streams reordered successfully")
        return {"success": success, "message": "Streams reordered successfully"}
    except ValueError as e:
        logger.warning(f"Invalid reorder request: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Reorder failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder streams"
        )

@router.get("/ffmpeg-defaults")
async def get_ffmpeg_defaults() -> dict:
    """Get default FFmpeg parameters for detected GPU backend.
    
    Returns default parameters that will be used if user doesn't specify custom ones.
    This is the single source of truth for FFmpeg configuration.
    """
    backend = get_gpu_backend()
    
    logger.debug(f"FFmpeg defaults query: GPU={backend}")
    
    return {
        "gpu_backend": backend,
        "base_params": list(BASE_FFMPEG_PARAMS),
        "gpu_params": GPU_FFMPEG_PARAMS.get(backend, []),
        "combined_params": get_default_ffmpeg_params_string(backend),
        "combined_params_array": get_default_ffmpeg_params_string(backend).split(),
    }

# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("")
async def list_streams(
    service: StreamsService = Depends(get_streams_service)
) -> list[dict]:
    """List all configured streams with masked credentials."""
    try:
        logger.debug("Listing streams")
        streams = await service.list_streams()
        logger.debug(f"Listed {len(streams)} stream(s)")
        return [mask_stream_response(stream) for stream in streams]
    except Exception as e:
        logger.error(f"List failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list streams"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_stream(
    new_stream: NewStream,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Create a new stream with GPU validation."""
    try:
        logger.info(f"Creating stream: {new_stream.name}")
        
        # Validate configuration (includes GPU check)
        await validate_stream_config(
            rtsp_url=new_stream.rtsp_url,
            ffmpeg_params=new_stream.ffmpeg_params,
        )
        
        stream = await service.create_stream(
            name=new_stream.name,
            rtsp_url=new_stream.rtsp_url,
            ffmpeg_params=new_stream.ffmpeg_params
        )
        
        logger.info(f"Stream created: {stream['name']} ({stream['id']})")
        return mask_stream_response(stream)
    except RuntimeError as e:
        logger.warning(f"Create failed - GPU unavailable: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except ValueError as e:
        logger.warning(f"Create failed - validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Create failed: {e}", exc_info=True)
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
        logger.debug(f"Getting stream: {stream_id}")
        stream = await service.get_stream(stream_id)
        if not stream:
            logger.warning(f"Stream not found: {stream_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
        return mask_stream_response(stream)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get failed for {stream_id}: {e}", exc_info=True)
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
    """Update stream (partial). Auto-restarts if parameters change while running."""
    try:
        logger.info(f"Updating stream: {stream_id}")
        
        current = await service.get_stream(stream_id)
        if not current:
            logger.warning(f"Update failed - not found: {stream_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
        
        # Check if restart needed
        needs_restart = False
        was_running = current["status"] == "running"
        
        if was_running:
            # URL changed
            if edit_stream.rtsp_url and edit_stream.rtsp_url != current["rtsp_url"]:
                needs_restart = True
                logger.info(f"RTSP URL changed for {stream_id}, restart required")
            
            # FFmpeg params changed
            if edit_stream.ffmpeg_params is not None:
                if set(current.get("ffmpeg_params", [])) != set(edit_stream.ffmpeg_params):
                    needs_restart = True
                    logger.info(f"FFmpeg params changed for {stream_id}, restart required")
        
        # Stop if restart needed
        if needs_restart:
            logger.info(f"Stopping {stream_id} for parameter update")
            await service.stop_stream(stream_id)
        
        # Re-validate if critical params changed
        if edit_stream.rtsp_url is not None or edit_stream.ffmpeg_params is not None:
            url = edit_stream.rtsp_url or current["rtsp_url"]
            params = edit_stream.ffmpeg_params or current.get("ffmpeg_params", [])
            await validate_stream_config(url, params)
        
        # Update
        updated = await service.update_stream(
            stream_id=stream_id,
            name=edit_stream.name,
            rtsp_url=edit_stream.rtsp_url,
            status=edit_stream.status,
            ffmpeg_params=edit_stream.ffmpeg_params
        )
        
        if not updated:
            logger.warning(f"Update failed - not found: {stream_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
        
        # Restart if needed
        if needs_restart:
            logger.info(f"Restarting {stream_id} with new parameters")
            success = await service.start_stream(stream_id, updated)
            if not success:
                logger.error(f"Restart failed for {stream_id}")
        
        logger.info(f"Stream updated: {stream_id}")
        return mask_stream_response(updated)
    except RuntimeError as e:
        logger.warning(f"Update failed - GPU unavailable: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except ValueError as e:
        logger.warning(f"Update failed - validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update failed for {stream_id}: {e}", exc_info=True)
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
        logger.info(f"Deleting stream: {stream_id}")
        deleted = await service.delete_stream(stream_id)
        if not deleted:
            logger.warning(f"Delete failed - not found: {stream_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
        logger.info(f"Stream deleted: {stream_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed for {stream_id}: {e}", exc_info=True)
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
    """Start FFmpeg stream processing with GPU acceleration."""
    try:
        logger.info(f"Starting stream: {stream_id}")
        
        gpu_backend = get_gpu_backend()
        if gpu_backend == "none":
            logger.warning(f"Start failed - GPU unavailable for {stream_id}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GPU backend not detected"
            )
        
        stream = await service.get_stream(stream_id)
        if not stream:
            logger.warning(f"Start failed - not found: {stream_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
        
        if stream["status"] == "running":
            logger.debug(f"Stream already running: {stream_id}")
            return {"message": "Stream already running", "status": "running"}
        
        async with _start_lock:
            active = len(service.active_processes)
            logger.debug(f"Active streams: {active}/{MAX_CONCURRENT_STREAMS}")
            
            if active >= MAX_CONCURRENT_STREAMS:
                logger.warning(f"Max streams reached: {active}/{MAX_CONCURRENT_STREAMS}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Maximum concurrent streams ({MAX_CONCURRENT_STREAMS}) reached"
                )
            
            success = await service.start_stream(stream_id, stream)
            if not success:
                logger.error(f"Start failed for {stream_id}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to start stream processing"
                )
        
        logger.info(f"Stream started: {stream_id}")
        return {"message": "Stream started successfully", "status": "running", "gpu_backend": gpu_backend}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Start failed for {stream_id}: {e}", exc_info=True)
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
        logger.info(f"Stopping stream: {stream_id}")
        
        stream = await service.get_stream(stream_id)
        if not stream:
            logger.warning(f"Stop failed - not found: {stream_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
        
        if stream["status"] != "running":
            logger.debug(f"Stream already stopped: {stream_id}")
            return {"message": "Stream not running", "status": "stopped"}
        
        success = await service.stop_stream(stream_id)
        if not success:
            logger.error(f"Stop failed for {stream_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to stop stream"
            )
        
        logger.info(f"Stream stopped: {stream_id}")
        return {"message": "Stream stopped successfully", "status": "stopped"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stop failed for {stream_id}: {e}", exc_info=True)
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
    show_motion: bool = True,
    show_tracking: bool = True,
    service: StreamsService = Depends(get_streams_service)
) -> StreamingResponse:
    """Stream MJPEG video at 5fps with optional visualization layers (T058-T061).

    Args:
        stream_id: Stream identifier
        show_motion: Show red boxes around motion regions (default: True)
        show_tracking: Show green/yellow boxes with IDs for tracked objects (default: True)
    """
    stream = await service.get_stream(stream_id)
    if not stream:
        logger.warning(f"MJPEG failed - not found: {stream_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")

    if stream["status"] != "running":
        logger.warning(f"MJPEG failed - not running: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream must be started first"
        )

    logger.info(f"Starting MJPEG stream: {stream_id} (motion={show_motion}, tracking={show_tracking})")

    async def generate_frames():
        """Generate MJPEG multipart stream at locked 5fps."""
        frame_count = 0  # Initialize before try block

        # Register viewer connection with visualization preferences (B1, B2 fix + T058-T061)
        service.register_mjpeg_viewer(stream_id, show_motion=show_motion, show_tracking=show_tracking)

        try:
            frame_interval = 1.0 / FPS
            last_time = 0.0

            while True:
                current_time = asyncio.get_event_loop().time()

                # Throttle to 5fps
                if last_time > 0:
                    elapsed = current_time - last_time
                    if elapsed < frame_interval:
                        await asyncio.sleep(frame_interval - elapsed)

                # Get latest processed frame (B7 optimization - JPEG encoding on demand)
                frame_data = await service.get_frame_for_mjpeg(stream_id)
                if frame_data is None:
                    logger.warning(f"MJPEG ended - no more frames: {stream_id}")
                    break

                success, jpeg_bytes = frame_data
                if not success or not jpeg_bytes:
                    await asyncio.sleep(0.1)
                    continue

                # Yield MJPEG multipart frame
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n'
                    b'Content-Length: ' + str(len(jpeg_bytes)).encode() + b'\r\n\r\n' +
                    jpeg_bytes + b'\r\n'
                )

                frame_count += 1
                last_time = asyncio.get_event_loop().time()

                # Log every 10 seconds
                if frame_count % 50 == 0:
                    logger.debug(f"MJPEG {stream_id}: {frame_count} frames")

        except asyncio.CancelledError:
            logger.info(f"MJPEG cancelled: {stream_id} ({frame_count} frames)")
            raise
        except Exception as e:
            logger.error(f"MJPEG error for {stream_id}: {e}", exc_info=True)
        finally:
            # Unregister viewer on disconnect (B1, B2 fix)
            service.unregister_mjpeg_viewer(stream_id)

    
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
    """Get single JPEG snapshot for dashboard thumbnails."""
    logger.info(f"Snapshot request: {stream_id}")
    
    stream = await service.get_stream(stream_id)
    if not stream:
        logger.warning(f"Snapshot failed - not found: {stream_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
    
    if stream["status"] != "running":
        logger.warning(f"Snapshot failed - not running: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream must be started first"
        )
    
    try:
        # Retry up to 3 times with timeout
        jpeg_bytes = None
        
        for attempt in range(SNAPSHOT_MAX_RETRIES):
            logger.debug(f"Snapshot attempt {attempt + 1}/{SNAPSHOT_MAX_RETRIES}: {stream_id}")
            
            frame_data = await asyncio.wait_for(
                service.get_frame(stream_id),
                timeout=SNAPSHOT_TIMEOUT
            )
            
            if frame_data is None:
                logger.debug(f"Attempt {attempt + 1}: get_frame returned None")
                continue
            
            success, frame_bytes = frame_data
            if success and frame_bytes:
                jpeg_bytes = frame_bytes
                logger.info(f"Snapshot captured: {stream_id} ({len(jpeg_bytes)} bytes)")
                break
            
            await asyncio.sleep(0.2)
        
        if not jpeg_bytes:
            logger.error(f"Snapshot failed - no frame after {SNAPSHOT_MAX_RETRIES} retries: {stream_id}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to capture frame"
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
        logger.error(f"Snapshot timeout: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Snapshot timeout - stream may be stalled"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Snapshot error for {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to capture snapshot"
        )


@router.get("/{stream_id}/scores")
async def stream_scores_sse(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> StreamingResponse:
    """SSE endpoint for real-time detection scores (placeholder for YOLO)."""
    stream = await service.get_stream(stream_id)
    if not stream:
        logger.warning(f"SSE failed - not found: {stream_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stream not found")
    
    if stream["status"] != "running":
        logger.warning(f"SSE failed - not running: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream must be started first"
        )
    
    logger.info(f"Starting SSE stream: {stream_id}")
    
    async def event_generator():
        """Generate SSE events with detection scores (placeholder data)."""
        event_count = 0  # Initialize before try block
        try:
            while True:
                frame_data = await service.get_frame(stream_id)
                if frame_data is None:
                    logger.info(f"SSE ended: {stream_id}")
                    break
                
                ret, frame = frame_data
                if not ret or frame is None:
                    break
                
                # TODO: Replace with actual YOLO + Shapely detection
                score = {
                    "stream_id": stream_id,
                    "zone_id": None,
                    "object_class": "person",
                    "confidence": random.uniform(0.7, 0.99),
                    "distance": random.uniform(0, 1),
                    "coordinates": {"x": random.uniform(0, 1), "y": random.uniform(0, 1)},
                    "size": random.randint(50, 200),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                yield f"data: {json.dumps(score)}\n\n"
                
                event_count += 1
                if event_count % 50 == 0:
                    logger.debug(f"SSE {stream_id}: {event_count} events")
                
                await asyncio.sleep(1.0 / FPS)
        except asyncio.CancelledError:
            logger.info(f"SSE cancelled: {stream_id} ({event_count} events)")
            raise
        except Exception as e:
            logger.error(f"SSE error for {stream_id}: {e}", exc_info=True)

    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# Motion Detection Metrics Endpoints (Feature 006)
# ============================================================================

@router.get("/{stream_id}/motion/metrics")
async def get_motion_metrics(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Get current motion detection metrics for stream.

    Returns:
        MotionDetectionMetrics with counts, timing, and GPU utilization

    Raises:
        404: Stream not found
        503: Stream not running or motion detection not initialized
        429: Rate limit exceeded (10 requests/second per stream)
    """
    # T066: Rate limiting check
    if not motion_metrics_limiter.check_rate_limit(stream_id):
        logger.warning(f"Rate limit exceeded for motion metrics: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 10 requests per second per stream."
        )

    logger.debug(f"Motion metrics request: {stream_id}")

    # Check if stream exists
    stream = await service.get_stream(stream_id)
    if not stream:
        logger.warning(f"Motion metrics failed - not found: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found"
        )

    # Check if stream is running
    if stream["status"] != "running":
        logger.warning(f"Motion metrics failed - not running: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stream must be started first"
        )

    # Get metrics from active process
    try:
        metrics = service.get_motion_metrics(stream_id)
        if metrics is None:
            logger.warning(f"Motion metrics not available: {stream_id}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Motion detection not initialized"
            )

        logger.debug(f"Motion metrics returned: {stream_id}")
        return metrics.model_dump()
    except Exception as e:
        logger.error(f"Motion metrics error for {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get motion metrics"
        )


@router.get("/{stream_id}/motion/metrics/stream")
async def stream_motion_metrics_sse(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> StreamingResponse:
    """SSE endpoint for real-time motion detection metrics at 5 FPS.

    Streams MotionDetectionMetrics updates every 200ms for live dashboard display.
    """
    stream = await service.get_stream(stream_id)
    if not stream:
        logger.warning(f"Motion metrics SSE failed - not found: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found"
        )

    if stream["status"] != "running":
        logger.warning(f"Motion metrics SSE failed - not running: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stream must be started first"
        )

    logger.info(f"Starting motion metrics SSE: {stream_id}")

    async def event_generator():
        """Generate SSE events with motion metrics at 5 FPS."""
        event_count = 0
        try:
            while True:
                metrics = service.get_motion_metrics(stream_id)
                if metrics is None:
                    logger.warning(f"Motion metrics SSE ended - no metrics: {stream_id}")
                    break

                # Send metrics as SSE event
                yield f"data: {metrics.model_dump_json()}\n\n"

                event_count += 1
                if event_count % 50 == 0:
                    logger.debug(f"Motion metrics SSE {stream_id}: {event_count} events")

                # 5 FPS = 200ms interval
                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            logger.info(f"Motion metrics SSE cancelled: {stream_id} ({event_count} events)")
            raise
        except Exception as e:
            logger.error(f"Motion metrics SSE error for {stream_id}: {e}", exc_info=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{stream_id}/motion/objects")
async def get_tracked_objects(
    stream_id: str,
    state: str | None = None,
    service: StreamsService = Depends(get_streams_service)
) -> list[dict]:
    """Get currently tracked objects for stream.

    Args:
        stream_id: Stream identifier
        state: Optional filter by ObjectState (tentative, active, stationary, lost)

    Returns:
        List of TrackedObject instances (serialized)

    Raises:
        404: Stream not found
        503: Stream not running or tracking not initialized
        429: Rate limit exceeded (10 requests/second per stream)
    """
    # T066: Rate limiting check
    if not motion_metrics_limiter.check_rate_limit(stream_id):
        logger.warning(f"Rate limit exceeded for tracked objects: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 10 requests per second per stream."
        )

    logger.debug(f"Tracked objects request: {stream_id}, state={state}")

    # Check if stream exists
    stream = await service.get_stream(stream_id)
    if not stream:
        logger.warning(f"Tracked objects failed - not found: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stream not found"
        )

    # Check if stream is running
    if stream["status"] != "running":
        logger.warning(f"Tracked objects failed - not running: {stream_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stream must be started first"
        )

    # Get tracked objects from active process
    try:
        tracked_objects = service.get_tracked_objects(stream_id, state_filter=state)
        if tracked_objects is None:
            logger.warning(f"Tracked objects not available: {stream_id}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Object tracking not initialized"
            )

        logger.debug(f"Tracked objects returned: {stream_id}, count={len(tracked_objects)}")
        return [obj.model_dump() for obj in tracked_objects]
    except ValueError as e:
        logger.warning(f"Invalid state filter: {state}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Tracked objects error for {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tracked objects"
        )


logger.debug("Stream management router initialized")
