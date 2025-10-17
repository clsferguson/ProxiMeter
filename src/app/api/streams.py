"""REST API endpoints for stream management."""
from fastapi import APIRouter, HTTPException, status
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streams", tags=["streams"])


# Placeholder endpoints - will be implemented in Phase 3 and 4
@router.get("/")
async def list_streams():
    """List all streams."""
    # TODO: Implement in T040
    return []


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_stream():
    """Create a new stream."""
    # TODO: Implement in T029
    raise HTTPException(status_code=501, detail="Not implemented")


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
