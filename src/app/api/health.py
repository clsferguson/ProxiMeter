"""Health check endpoint."""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List
import logging

# Correct imports based on your actual structure
from ..services.streams_service import StreamsService
from ..config_io import get_gpu_backend

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

def get_streams_service() -> StreamsService:
    """Dependency to get streams service instance."""
    return StreamsService()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(
    service: StreamsService = Depends(get_streams_service)
) -> Dict[str, Any]:
    """Health check with stream statuses and acceleration modes.
    
    Returns:
        - status: "healthy" if all streams operational, "degraded" if any errors
        - streams: List of stream details with ID, status, and acceleration mode
        - active_streams: Count of currently running streams
        - total_streams: Total number of configured streams
    
    Raises:
        HTTPException: 503 Service Unavailable if health check fails critically
    """
    try:
        streams = await service.list_streams()
        
        # Get GPU backend once for efficiency
        gpu_backend = get_gpu_backend()
        
        # Build stream details with proper type hints
        stream_details: List[Dict[str, str]] = []
        for s in streams:
            accel = "software"
            if s.get("hw_accel_enabled", False):
                if gpu_backend != "none":
                    accel = gpu_backend  # e.g., "nvidia", "amd", "intel"
                else:
                    accel = "software (GPU unavailable)"
            
            stream_details.append({
                "id": s["id"],
                "status": s["status"],
                "accel": accel
            })
        
        # Determine overall health status
        has_errors = any(s["status"] == "error" for s in streams)
        overall_status = "degraded" if has_errors else "healthy"
        
        # Count active streams
        active_count = sum(1 for s in streams if s["status"] == "running")
        
        return {
            "status": overall_status,
            "streams": stream_details,
            "active_streams": active_count,
            "total_streams": len(streams),
            "gpu_backend": gpu_backend
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        # Return 503 Service Unavailable for critical failures
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )

@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe() -> Dict[str, str]:
    """Kubernetes liveness probe - checks if the service is alive.
    
    Returns a simple response indicating the service is running.
    This doesn't check dependencies, just that the process is responsive.
    """
    return {"status": "alive"}

@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_probe(
    service: StreamsService = Depends(get_streams_service)
) -> Dict[str, Any]:
    """Kubernetes readiness probe - checks if service can accept traffic.
    
    Verifies that the service and its dependencies are ready to handle requests.
    
    Raises:
        HTTPException: 503 if service is not ready
    """
    try:
        # Quick check that service is operational
        streams = await service.list_streams()
        
        return {
            "status": "ready",
            "total_streams": len(streams)
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
