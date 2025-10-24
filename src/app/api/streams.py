"""REST API endpoints for stream management."""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse, Response
from typing import List
import logging
from threading import Lock
import asyncio
import json
import random
from datetime import datetime
import cv2

from ..models.stream import NewStream, Stream, EditStream
from ..models.zone import Zone, NewZone, EditZone
from ..services.streams_service import StreamsService
from ..services.zones_service import ZonesService
from ..utils.rtsp import generate_mjpeg_stream
from ..utils.strings import mask_rtsp_credentials
from ..metrics import generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streams", tags=["streams"])

# Global lock for concurrent starts
_start_lock = Lock()


def get_streams_service() -> StreamsService:
    """Dependency to get streams service instance."""
    return StreamsService()


@router.get("", response_model=List[dict])
async def list_streams(
    service: StreamsService = Depends(get_streams_service)
):
    """List all streams with masked credentials.
    
    Returns streams sorted by order field.
    Credentials in rtsp_url are masked in responses.
    """
    try:
        streams = await service.list_streams()
        
        # Mask credentials in all responses
        for stream in streams:
            if "rtsp_url" in stream:
                stream["rtsp_url"] = mask_rtsp_credentials(stream["rtsp_url"])
        
        return streams
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
):
    """Create a new stream with FFmpeg validation.
    
    Validates name, RTSP URL, params; constructs FFmpeg command with GPU flags if enabled;
    rejects incompatible params with 400. Probes connectivity.
    Returns stream with status 'stopped' initially.
    Credentials in rtsp_url are masked in the response.
    """
    try:
        from ..utils.rtsp import validate_rtsp_url, build_ffmpeg_command
        from ..config_io import get_gpu_backend
        
        gpu_backend = get_gpu_backend()
        
        # Validate params if provided
        params = new_stream.ffmpeg_params or []
        if not validate_rtsp_url(new_stream.rtsp_url, params, gpu_backend):
            raise ValueError("Invalid RTSP URL or FFmpeg parameters")
        
        # Build command to check compatibility (dry-run probe)
        cmd = build_ffmpeg_command(
            rtsp_url=new_stream.rtsp_url,
            ffmpeg_params=params,
            target_fps=new_stream.target_fps,
            gpu_backend=gpu_backend if new_stream.hw_accel_enabled else None
        )
        # Note: Full validation via ffprobe in service if needed
        
        stream = await service.create_stream(
            name=new_stream.name,
            rtsp_url=new_stream.rtsp_url,
            hw_accel_enabled=new_stream.hw_accel_enabled,
            ffmpeg_params=params,
            target_fps=new_stream.target_fps
        )
        
        # Mask credentials in response
        stream_response = stream.copy()
        stream_response["rtsp_url"] = mask_rtsp_credentials(stream.get("rtsp_url", ""))
        
        return stream_response
    except ValueError as e:
        # Validation errors (duplicate name, invalid URL, params, etc.)
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


@router.put("/{stream_id}")
async def update_stream(
    stream_id: str,
    edit_stream: EditStream,
    service: StreamsService = Depends(get_streams_service)
):
    """Update an existing stream (partial update).
    
    Validates updated config, re-validates params if changed.
    Returns updated stream with masked credentials.
    """
    try:
        from ..utils.rtsp import validate_rtsp_url
        from ..config_io import get_gpu_backend
        
        gpu_backend = get_gpu_backend()
        updated = False
        
        # If URL or params changed, re-validate
        if edit_stream.rtsp_url is not None or edit_stream.ffmpeg_params is not None:
            current_stream = await service.get_stream(stream_id)
            if not current_stream:
                raise HTTPException(status_code=404, detail="Stream not found")
            
            url = edit_stream.rtsp_url or current_stream["rtsp_url"]
            params = edit_stream.ffmpeg_params or current_stream.get("ffmpeg_params", [])
            
            if not validate_rtsp_url(url, params, gpu_backend):
                raise ValueError("Invalid RTSP URL or FFmpeg parameters after update")
            
            updated = True
        
        # Update via service
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
        
        # Mask credentials in response
        updated_stream["rtsp_url"] = mask_rtsp_credentials(updated_stream.get("rtsp_url", ""))
        
        return updated_stream
    except ValueError as e:
        # Validation errors
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
):
    """Delete a stream and renumber remaining streams.
    
    Returns 204 No Content on success.
    Returns 404 if stream not found.
    """
    try:
        deleted = await service.delete_stream(stream_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stream {stream_id} not found"
            )
        
        # Return 204 No Content (no body)
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete stream"
        )


@router.post("reorder")
async def reorder_streams(
    reorder_data: dict,
    service: StreamsService = Depends(get_streams_service)
):
    """Reorder streams by ID list.
    
    Accepts { "order": ["uuid1", "uuid2", ...] }
    Idempotent - returns 200 if order unchanged or ≤1 streams.
    Returns 400 if order contains duplicates or missing IDs.
    """
    try:
        order = reorder_data.get("order", [])
        
        if not isinstance(order, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order must be a list of stream IDs"
            )
        
        # Reorder streams
        success = await service.reorder_streams(order)
        
        return {"success": success, "message": "Streams reordered successfully"}
    except ValueError as e:
        # Validation errors (duplicates, missing IDs, etc.)
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


@router.get("/{stream_id}/mjpeg")
async def mjpeg_stream(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
):
    """Stream MJPEG for a specific stream from FFmpeg pipe.
    
    Returns multipart/x-mixed-replace with JPEG frames (640x480, 80% quality) at target FPS.
    """
    stream = await service.get_stream(stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    if stream["status"] != "running":
        raise HTTPException(status_code=400, detail="Stream not started")
    
    fps = stream.get("target_fps", 5)
    
    async def generate_frames():
        while True:
            ret, frame = await service.get_frame(stream_id)
            if not ret:
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + b''  # Empty frame or break
                break
            
            # Resize to 640x480
            height, width = frame.shape[:2]
            if width != 640 or height != 480:
                frame = cv2.resize(frame, (640, 480))
            
            # Encode JPEG 80% quality
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue
            
            yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n' + jpeg.tobytes() + b'\r\n'
            await asyncio.sleep(1 / fps)
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@router.get("/{stream_id}/scores")
async def scores_sse(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
):
    """SSE endpoint for real-time scores at 5 FPS."""
    stream = await service.get_stream(stream_id)
    if not stream or stream["status"] != "running":
        raise HTTPException(400, "Stream not running")
    
    async def event_generator():
        while True:
            ret, frame = await service.get_frame(stream_id)
            if not ret:
                break
            
            # Dummy scoring (replace with YOLO + Shapely)
            distance = random.uniform(0, 1)
            coords = {"x": random.uniform(0, 1), "y": random.uniform(0, 1)}
            size = random.randint(50, 200)
            
            score = {"distance": distance, "coordinates": coords, "size": size, "timestamp": datetime.utcnow().isoformat()}
            yield f"data: {json.dumps(score)}\n\n"
            await asyncio.sleep(0.2)  # 5 FPS
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )




@router.get("/gpu-backend")
async def get_gpu_backend():
    """Get detected GPU backend for UI defaults."""
    from ..config_io import get_gpu_backend
    backend = get_gpu_backend()
    return {"gpu_backend": backend}


@router.post("/{stream_id}/start", status_code=status.HTTP_200_OK)
async def start_stream(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
):
    """Start processing for a stream.
    
    Launches FFmpeg subprocess, updates status to 'running'.
    Enforces max 4 concurrent streams with locking.
    """
    try:
        stream = await service.get_stream(stream_id)
        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found")
        
        if stream["status"] == "running":
            return {"message": "Stream already running"}
        
        with _start_lock:
            if len(service.active_processes) >= 4:
                raise HTTPException(
                    status_code=409,
                    detail="Maximum concurrent streams (4) reached"
                )
            
            success = await service.start_stream(stream_id, stream)
            if not success:
                raise HTTPException(
                    status_code=503,
                    detail="Failed to start stream processing (GPU unavailable?)"
                )
        
        return {"message": "Stream started successfully", "status": "running"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting stream {stream_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{stream_id}/stop", status_code=status.HTTP_200_OK)
async def stop_stream(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
):
    """Stop processing for a stream.
    
    Terminates FFmpeg subprocess, updates status to 'stopped'.
    """
    try:
        stream = await service.get_stream(stream_id)
        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found")
        
        if stream["status"] != "running":
            return {"message": "Stream not running"}
        
        success = await service.stop_stream(stream_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to stop stream")
        
        return {"message": "Stream stopped successfully", "status": "stopped"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping stream {stream_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from ..metrics import get_metrics
    body, status_code, headers = get_metrics()
    return Response(content=body, status_code=status_code, headers=headers)
