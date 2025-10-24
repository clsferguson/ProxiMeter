"""Health check and monitoring endpoints."""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List, Literal
import logging

from ..services.streams_service import StreamsService
from ..config_io import get_gpu_backend

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Type aliases for better readability
HealthStatus = Literal["healthy", "degraded", "unhealthy"]
ProbeStatus = Literal["alive", "ready"]


def get_streams_service() -> StreamsService:
    """Dependency injection for streams service."""
    return StreamsService()


def determine_acceleration_mode(stream: dict, gpu_backend: str) -> str:
    """Determine the acceleration mode for a stream.
    
    Args:
        stream: Stream configuration dict
        gpu_backend: Detected GPU backend (nvidia/amd/intel/none)
        
    Returns:
        Human-readable acceleration mode string
    """
    if not stream.get("hw_accel_enabled", False):
        return "software"
    
    if gpu_backend == "none":
        return "software (GPU unavailable)"
    
    return gpu_backend


def calculate_health_status(streams: List[dict]) -> HealthStatus:
    """Calculate overall health status based on stream states.
    
    Args:
        streams: List of stream configurations
        
    Returns:
        Overall health status
    """
    if not streams:
        return "healthy"
    
    error_count = sum(1 for s in streams if s.get("status") == "error")
    
    if error_count == 0:
        return "healthy"
    elif error_count < len(streams):
        return "degraded"
    else:
        return "unhealthy"


# ============================================================================
# Health Check Endpoints
# ============================================================================

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(
    service: StreamsService = Depends(get_streams_service)
) -> Dict[str, Any]:
    """Comprehensive health check with stream statuses.
    
    Returns detailed health information including:
    - Overall service status (healthy/degraded/unhealthy)
    - Individual stream statuses and acceleration modes
    - Active and total stream counts
    - GPU backend information
    
    Returns:
        Health status dictionary
        
    Raises:
        HTTPException 503: Critical service failure
    """
    try:
        streams = await service.list_streams()
        gpu_backend = get_gpu_backend()
        
        # Build detailed stream information
        stream_details: List[Dict[str, str]] = [
            {
                "id": stream["id"],
                "name": stream.get("name", "Unknown"),
                "status": stream.get("status", "unknown"),
                "acceleration": determine_acceleration_mode(stream, gpu_backend)
            }
            for stream in streams
        ]
        
        # Calculate metrics
        overall_status = calculate_health_status(streams)
        active_count = sum(1 for s in streams if s.get("status") == "running")
        error_count = sum(1 for s in streams if s.get("status") == "error")
        
        response = {
            "status": overall_status,
            "gpu_backend": gpu_backend,
            "streams": stream_details,
            "metrics": {
                "total": len(streams),
                "active": active_count,
                "stopped": len(streams) - active_count - error_count,
                "error": error_count
            }
        }
        
        # Log health status
        if overall_status != "healthy":
            logger.warning(
                f"Health check shows {overall_status} status: "
                f"{error_count} errors, {active_count}/{len(streams)} active"
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe() -> Dict[str, ProbeStatus]:
    """Kubernetes liveness probe.
    
    Simple endpoint that returns immediately to verify the service process
    is running and responsive. Does not check dependencies or functionality.
    
    Use this for Kubernetes liveness probes to restart unhealthy pods.
    
    Returns:
        Liveness status
    """
    return {"status": "alive"}


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_probe(
    service: StreamsService = Depends(get_streams_service)
) -> Dict[str, Any]:
    """Kubernetes readiness probe.
    
    Verifies the service and its dependencies are ready to handle requests.
    Checks that the service can successfully query stream configurations.
    
    Use this for Kubernetes readiness probes to control traffic routing.
    
    Returns:
        Readiness status with basic metrics
        
    Raises:
        HTTPException 503: Service not ready
    """
    try:
        # Verify service can query streams
        streams = await service.list_streams()
        gpu_backend = get_gpu_backend()
        
        return {
            "status": "ready",
            "gpu_backend": gpu_backend,
            "total_streams": len(streams)
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get("/health/startup", status_code=status.HTTP_200_OK)
async def startup_probe(
    service: StreamsService = Depends(get_streams_service)
) -> Dict[str, ProbeStatus]:
    """Kubernetes startup probe.
    
    Used during container initialization to determine when the application
    has started successfully. Similar to readiness but with more lenient
    timeout expectations.
    
    Returns:
        Startup status
        
    Raises:
        HTTPException 503: Service not started
    """
    try:
        # Basic initialization check
        await service.list_streams()
        
        return {"status": "ready"}
        
    except Exception as e:
        logger.error(f"Startup check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not started"
        )
