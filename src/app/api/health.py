"""Health check endpoint."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint for container orchestration.
    
    Returns:
        dict: Status object with "status": "ok"
    """
    return {"status": "ok"}
