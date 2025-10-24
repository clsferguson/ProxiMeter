"""REST API endpoints for stream management."""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse, Response
from typing import List, Optional
import logging
import asyncio
import json
import random
from datetime import datetime
import cv2

from ..models.stream import NewStream, Stream, EditStream
from ..services.streams_service import StreamsService
from ..utils.rtsp import validate_rtsp_url, build_ffmpeg_command
from ..utils.strings import mask_rtsp_credentials
from ..config_io import get_gpu_backend

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streams"])

# Global asyncio lock for concurrent stream starts
_start_lock = asyncio.Lock()

# Constants
MAX_CONCURRENT_STREAMS = 4
MJPEG_FRAME_SIZE = (640, 480)
MJPEG_QUALITY = 80
SSE_FPS = 5


def get_streams_service() -> StreamsService:
    """Dependency injection for streams service."""
    return StreamsService()


async def validate_stream_config(
    rtsp_url: str,
    ffmpeg_params: Optional[List[str]],
    hw_accel_enabled: bool
) -> None:
    """Validate stream configuration.
    
    Args:
        rtsp_url: RTSP URL to validate
        ffmpeg_params: FFmpeg parameters
        hw_accel_enabled: Whether hardware acceleration is enabled
        
    Raises:
        ValueError: If configuration is invalid
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
    """Mask RTSP credentials in stream response.
    
    Args:
        stream: Stream dictionary
        
    Returns:
        Stream with masked credentials
    """
    masked = stream.copy()
    if "rtsp_url" in masked:
        masked["rtsp_url"] = mask_rtsp_credentials(masked["rtsp_url"])
    return masked


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("", response_model=List[dict])
async def list_streams(
    service: StreamsService = Depends(get_streams_service)
) -> List[dict]:
    """List all streams with masked credentials.
    
    Returns:
        List of streams sorted by order field with masked credentials
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
    """Create a new stream with validation.
    
    Args:
        new_stream: Stream configuration
        
    Returns:
        Created stream with masked credentials
        
    Raises:
        HTTPException 400: Invalid configuration
        HTTPException 500: Server error
    """
    try:
        # Validate configuration
        await validate_stream_config(
            rtsp_url=new_stream.rtsp_url,
            ffmpeg_params=new_stream.ffmpeg_params,
            hw_accel_enabled=new_stream.hw_accel_enabled
        )
        
        # Create stream
        stream = await service.create_stream(
            name=new_stream.name,
            rtsp_url=new_stream.rtsp_url,
            hw_accel_enabled=new_stream.hw_accel_enabled,
            ffmpeg_params=new_stream.ffmpeg_params or [],
            target_fps=new_stream.target_fps
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
        stream_id: Stream UUID
        
    Returns:
        Stream with masked credentials
        
    Raises:
        HTTPException 404: Stream not found
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


@router.put("/{stream_id}")
async def update_stream(
    stream_id: str,
    edit_stream: EditStream,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Update an existing stream (partial update).
    
    Args:
        stream_id: Stream UUID
        edit_stream: Fields to update
        
    Returns:
        Updated stream with masked credentials
        
    Raises:
        HTTPException 400: Invalid configuration
        HTTPException 404: Stream not found
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
            hw_accel = edit_stream.hw_accel_enabled if edit_stream.hw_accel_enabled is not None else current_stream.get("hw_accel_enabled", False)
            
            await validate_stream_config(url, params, hw_accel)
        
        # Update stream
        updated_stream = await service.update_stream(
            stream_id=stream_id,
            name=edit_stream.name,
            rtsp_url=edit_stream.rtsp_url,
            hw_accel_enabled=edit_stream.hw_accel_enabled,
            ffmpeg_params=edit_stream.ffmpeg_params,
            target_fps=edit_stream.target_fps
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
    """Delete a stream.
    
    Args:
        stream_id: Stream UUID
        
    Raises:
        HTTPException 404: Stream not found
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

@router.post("/{stream_id}/start", status_code=status.HTTP_200_OK)
async def start_stream(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Start stream processing.
    
    Args:
        stream_id: Stream UUID
        
    Returns:
        Success message and status
        
    Raises:
        HTTPException 404: Stream not found
        HTTPException 409: Maximum concurrent streams reached
        HTTPException 503: Failed to start
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


@router.post("/{stream_id}/stop", status_code=status.HTTP_200_OK)
async def stop_stream(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Stop stream processing.
    
    Args:
        stream_id: Stream UUID
        
    Returns:
        Success message and status
        
    Raises:
        HTTPException 404: Stream not found
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


@router.post("/reorder")
async def reorder_streams(
    reorder_data: dict,
    service: StreamsService = Depends(get_streams_service)
) -> dict:
    """Reorder streams.
    
    Args:
        reorder_data: {"order": ["uuid1", "uuid2", ...]}
        
    Returns:
        Success status
        
    Raises:
        HTTPException 400: Invalid order data
    """
    try:
        order = reorder_data.get("order", [])
        
        if not isinstance(order, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order must be a list of stream IDs"
            )
        
        success = await service.reorder_streams(order)
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
# Streaming Endpoints
# ============================================================================

def encode_frame_to_jpeg(frame) -> Optional[bytes]:
    """Encode frame to JPEG (blocking operation for thread pool).
    
    Args:
        frame: OpenCV frame
        
    Returns:
        JPEG bytes or None if encoding failed
    """
    try:
        height, width = frame.shape[:2]
        if width != MJPEG_FRAME_SIZE[0] or height != MJPEG_FRAME_SIZE[1]:
            frame = cv2.resize(frame, MJPEG_FRAME_SIZE)
        
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, MJPEG_QUALITY])
        if not ret:
            return None
        
        return jpeg.tobytes()
    except Exception as e:
        logger.error(f"Error encoding frame: {e}")
        return None


@router.get("/{stream_id}/mjpeg")
async def stream_mjpeg(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
) -> StreamingResponse:
    """Stream MJPEG for a specific stream.
    
    Args:
        stream_id: Stream UUID
        
    Returns:
        Multipart MJPEG stream
        
    Raises:
        HTTPException 400: Stream not running
        HTTPException 404: Stream not found
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
    
    fps = stream.get("target_fps", 5)
    
    async def generate_frames():
        try:
            while True:
                frame_data = await service.get_frame(stream_id)
                if frame_data is None:
                    break
                
                ret, frame = frame_data
                if not ret or frame is None:
                    break
                
                jpeg_bytes = await asyncio.to_thread(encode_frame_to_jpeg, frame)
                if jpeg_bytes is None:
                    continue
                
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n'
                    b'Content-Length: ' + str(len(jpeg_bytes)).encode() + b'\r\n\r\n' +
                    jpeg_bytes + b'\r\n'
                )
                await asyncio.sleep(1 / fps)
                
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
    
    Args:
        stream_id: Stream UUID
        
    Returns:
        Server-sent events stream
        
    Raises:
        HTTPException 400: Stream not running
        HTTPException 404: Stream not found
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
                    "timestamp": datetime.utcnow().isoformat()
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


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/gpu-backend")
async def get_gpu_info() -> dict:
    """Get detected GPU backend.
    
    Returns:
        GPU backend information
    """
    backend = get_gpu_backend()
    return {"gpu_backend": backend}


@router.get("/metrics")
async def get_prometheus_metrics() -> Response:
    """Prometheus metrics endpoint.
    
    Returns:
        Prometheus-formatted metrics
    """
    from ..metrics import get_metrics
    body, status_code, headers = get_metrics()
    return Response(content=body, status_code=status_code, headers=headers)
