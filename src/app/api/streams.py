"""REST API endpoints for stream management."""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from typing import List
import logging

from app.models.stream import NewStream, Stream
from app.services.streams_service import StreamsService
from app.utils.rtsp import generate_mjpeg_stream
from app.utils.strings import mask_rtsp_credentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streams", tags=["streams"])


def get_streams_service() -> StreamsService:
    """Dependency to get streams service instance."""
    return StreamsService()


# Placeholder endpoints - will be implemented in Phase 3 and 4
@router.get("/")
async def list_streams():
    """List all streams."""
    # TODO: Implement in T040
    return []


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_stream(
    new_stream: NewStream,
    service: StreamsService = Depends(get_streams_service)
):
    """Create a new stream.
    
    Validates name and RTSP URL, checks for duplicates, probes connectivity.
    Returns stream with status Active if reachable, Inactive otherwise.
    Credentials in rtsp_url are masked in the response.
    """
    try:
        stream = await service.create_stream(
            name=new_stream.name,
            rtsp_url=new_stream.rtsp_url
        )
        
        # Mask credentials in response
        stream_response = stream.copy()
        stream_response["rtsp_url"] = mask_rtsp_credentials(stream.get("rtsp_url", ""))
        
        return stream_response
    except ValueError as e:
        # Validation errors (duplicate name, invalid URL, etc.)
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


@router.patch("/{stream_id}")
async def edit_stream(stream_id: str):
    """Edit an existing stream."""
    # TODO: Implement in T042
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stream(stream_id: str):
    """Delete a stream."""
    # TODO: Implement in T041
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/reorder")
async def reorder_streams():
    """Reorder streams."""
    # TODO: Implement in T043
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/play/{stream_id}.mjpg")
async def playback_stream(
    stream_id: str,
    service: StreamsService = Depends(get_streams_service)
):
    """Stream MJPEG playback for a specific stream.
    
    Returns multipart/x-mixed-replace stream with JPEG frames at ≤5 FPS.
    """
    # Get stream from service
    stream = await service.get_stream(stream_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    
    rtsp_url = stream.get("rtsp_url")
    if not rtsp_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stream has no RTSP URL"
        )
    
    try:
        # Generate MJPEG stream with 5 FPS cap
        return StreamingResponse(
            generate_mjpeg_stream(rtsp_url, max_fps=5.0),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except Exception as e:
        logger.error(f"Playback error for stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start playback: {str(e)}"
        )
