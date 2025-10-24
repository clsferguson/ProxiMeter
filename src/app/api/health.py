"""Health check endpoint."""
from fastapi import APIRouter, HTTPException, Depends
from src.app.services.streams import StreamsService, get_streams_service
from src.app.utils.gpu import get_gpu_backend
from src.app.logger import logger

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(service: StreamsService = Depends(get_streams_service)):
    """Health check with stream statuses and acceleration modes."""
    try:
        streams = await service.list_streams()
        stream_details = []
        for s in streams:
            accel = "software"
            if s.get("hw_accel_enabled", False):
                gpu = get_gpu_backend()
                if gpu != "none":
                    accel = gpu  # e.g., "nvidia", "amd", "intel"
                else:
                    accel = "software (GPU unavailable)"
            stream_details.append({
                "id": s["id"],
                "status": s["status"],
                "accel": accel
            })
        
        return {
            "status": "healthy" if all(s["status"] != "error" for s in streams) else "degraded",
            "streams": stream_details,
            "active_streams": len([s for s in streams if s["status"] == "running"]),
            "total_streams": len(streams)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "details": str(e)}
