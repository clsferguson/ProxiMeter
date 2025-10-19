"""Health check endpoint."""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint for container orchestration.
    
    Returns:
        dict: Status object with "status": "ok"
    """
    return {"status": "ok"}


# Legacy counter endpoints - return 404
@router.get("/api/counter")
@router.post("/api/counter")
async def legacy_counter_endpoint():
    """Legacy counter endpoint removed in favor of RTSP stream management.
    
    Raises:
        HTTPException: 404 Not Found
    """
    raise HTTPException(
        status_code=404,
        detail="Counter feature has been removed. Use /api/streams instead."
    )
