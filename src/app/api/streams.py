"""REST API endpoints for stream management."""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from typing import List
import logging

from ..models.stream import NewStream, Stream
from ..services.streams_service import StreamsService
from ..utils.rtsp import generate_mjpeg_stream
from ..utils.strings import mask_rtsp_credentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streams", tags=["streams"])


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
async def edit_stream(
    stream_id: str,
    edit_data: dict,
    service: StreamsService = Depends(get_streams_service)
):
    """Edit an existing stream (partial update).
    
    Accepts partial updates for name and/or rtsp_url.
    Validates formats, checks uniqueness, re-probes if URL changed.
    Returns updated stream with masked credentials.
    """
    try:
        # Extract optional fields
        name = edit_data.get("name")
        rtsp_url = edit_data.get("rtsp_url")
        
        # Update stream
        updated_stream = await service.update_stream(
            stream_id=stream_id,
            name=name,
            rtsp_url=rtsp_url
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
        logger.error(f"Error editing stream {stream_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to edit stream"
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
        # Generate MJPEG stream with 5 FPS cap (pass stream_id for failure tracking)
        return StreamingResponse(
            generate_mjpeg_stream(rtsp_url, max_fps=5.0, stream_id=stream_id),
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
