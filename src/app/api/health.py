"""Health check and monitoring endpoints for service observability.

Provides Kubernetes-compatible health check endpoints for:
- Comprehensive health status with stream metrics
- Liveness probe (is process running?)
- Readiness probe (can service handle traffic?)
- Startup probe (has service finished initialization?)

Health Status Levels:
    - healthy: All streams operational
    - degraded: Some streams have errors
    - unhealthy: All streams have errors

Logging Strategy:
    DEBUG - Probe calls, health calculations, metrics gathering
    INFO  - Successful health checks (periodic noise in production)
    WARN  - Degraded/unhealthy status, stream errors
    ERROR - Health check failures, service unavailable

Kubernetes Integration:
    livenessProbe:  GET /health/live   (restart if fails)
    readinessProbe: GET /health/ready  (remove from load balancer if fails)
    startupProbe:   GET /health/startup (delay other probes until passes)

Usage:
    # Full health check with metrics
    >>> GET /health
    {
        "status": "healthy",
        "gpu_backend": "nvidia",
        "streams": [...],
        "metrics": {"total": 5, "active": 3, "stopped": 2, "error": 0}
    }
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List, Literal
import logging

from ..services.streams_service import StreamsService
from ..config_io import get_gpu_backend

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Type aliases for better readability and type safety
HealthStatus = Literal["healthy", "degraded", "unhealthy"]
ProbeStatus = Literal["alive", "ready"]


def get_streams_service() -> StreamsService:
    """Dependency injection for streams service.
    
    Returns singleton StreamsService instance for health checks.
    
    Returns:
        StreamsService instance
        
    Logs:
        DEBUG: Service injection
    """
    logger.debug("Injecting StreamsService for health check")
    return StreamsService()


def determine_acceleration_mode(stream: dict, gpu_backend: str) -> str:
    """Determine the acceleration mode for a stream.
    
    Checks if hardware acceleration is enabled and available.
    Returns human-readable description of acceleration status.
    
    Args:
        stream: Stream configuration dict
        gpu_backend: Detected GPU backend (nvidia/amd/intel/none)
        
    Returns:
        Human-readable acceleration mode string
        
    Examples:
        - "nvidia" (GPU available and enabled)
        - "software" (GPU disabled by config)
        - "software (GPU unavailable)" (GPU not detected)
        
    Logs:
        DEBUG: Acceleration mode determination
    """
    hw_accel = stream.get("hw_accel_enabled", False)
    
    if not hw_accel:
        logger.debug(f"Stream {stream.get('id', 'unknown')}: HW accel disabled")
        return "software"
    
    if gpu_backend == "none":
        logger.debug(f"Stream {stream.get('id', 'unknown')}: HW accel enabled but GPU unavailable")
        return "software (GPU unavailable)"
    
    logger.debug(f"Stream {stream.get('id', 'unknown')}: Using {gpu_backend} acceleration")
    return gpu_backend


def calculate_health_status(streams: List[dict]) -> HealthStatus:
    """Calculate overall health status based on stream states.
    
    Health levels:
    - healthy: No errors
    - degraded: Some errors but not all
    - unhealthy: All streams in error state
    
    Args:
        streams: List of stream configurations
        
    Returns:
        Overall health status
        
    Logs:
        DEBUG: Health calculation details
        WARN: Degraded or unhealthy status
    """
    if not streams:
        logger.debug("No streams configured, status: healthy")
        return "healthy"
    
    error_count = sum(1 for s in streams if s.get("status") == "error")
    total = len(streams)
    
    if error_count == 0:
        logger.debug(f"All {total} stream(s) operational, status: healthy")
        return "healthy"
    elif error_count < total:
        logger.warning(f"{error_count}/{total} stream(s) in error state, status: degraded")
        return "degraded"
    else:
        logger.warning(f"All {total} stream(s) in error state, status: unhealthy")
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
    
    This is the primary health check endpoint for monitoring.
    Use for comprehensive service health assessment.
    
    Returns:
        Health status dictionary with full metrics
        
    Raises:
        HTTPException 503: Critical service failure
        
    Example Response:
        {
            "status": "healthy",
            "gpu_backend": "nvidia",
            "streams": [
                {
                    "id": "abc-123",
                    "name": "Camera 1",
                    "status": "running",
                    "acceleration": "nvidia"
                }
            ],
            "metrics": {
                "total": 5,
                "active": 3,
                "stopped": 2,
                "error": 0
            }
        }
        
    Logs:
        DEBUG: Health check invocation and metrics
        WARN: Degraded or unhealthy status
        ERROR: Health check failures
    """
    try:
        logger.debug("Processing comprehensive health check")
        
        streams = await service.list_streams()
        gpu_backend = get_gpu_backend()
        
        logger.debug(f"Retrieved {len(streams)} stream(s) for health check")
        
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
        stopped_count = len(streams) - active_count - error_count
        
        response = {
            "status": overall_status,
            "gpu_backend": gpu_backend,
            "streams": stream_details,
            "metrics": {
                "total": len(streams),
                "active": active_count,
                "stopped": stopped_count,
                "error": error_count
            }
        }
        
        # Log non-healthy status as warning
        if overall_status != "healthy":
            logger.warning(
                f"Health check: {overall_status} status - "
                f"{error_count} errors, {active_count}/{len(streams)} active"
            )
        else:
            logger.debug(
                f"Health check: {overall_status} - "
                f"{active_count}/{len(streams)} active, {error_count} errors"
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Health check failed with exception: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_probe() -> Dict[str, ProbeStatus]:
    """Kubernetes liveness probe.
    
    Simple endpoint that returns immediately to verify the service process
    is running and responsive. Does not check dependencies or functionality.
    
    Kubernetes uses this to restart unhealthy pods. Failures indicate the
    process is deadlocked or crashed.
    
    Use this for:
    - Kubernetes livenessProbe configuration
    - Basic "is alive" checks
    - High-frequency health monitoring (low overhead)
    
    Returns:
        Liveness status (always {"status": "alive"})
        
    Logs:
        DEBUG: Liveness probe calls
    """
    logger.debug("Liveness probe called")
    return {"status": "alive"}


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_probe(
    service: StreamsService = Depends(get_streams_service)
) -> Dict[str, Any]:
    """Kubernetes readiness probe.
    
    Verifies the service and its dependencies are ready to handle requests.
    Checks that the service can successfully query stream configurations.
    
    Kubernetes uses this to control traffic routing. Failed probes remove
    the pod from the service's load balancer.
    
    Use this for:
    - Kubernetes readinessProbe configuration
    - Load balancer health checks
    - Dependency validation
    
    Returns:
        Readiness status with basic metrics
        
    Raises:
        HTTPException 503: Service not ready
        
    Example Response:
        {
            "status": "ready",
            "gpu_backend": "nvidia",
            "total_streams": 5
        }
        
    Logs:
        DEBUG: Readiness checks and results
        ERROR: Readiness failures
    """
    try:
        logger.debug("Processing readiness probe")
        
        # Verify service can query streams (tests config loading)
        streams = await service.list_streams()
        gpu_backend = get_gpu_backend()
        
        logger.debug(
            f"Readiness check passed: {len(streams)} stream(s), "
            f"GPU backend: {gpu_backend}"
        )
        
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
    
    Kubernetes delays liveness/readiness probes until this passes, allowing
    for slow application startup without premature restarts.
    
    Use this for:
    - Kubernetes startupProbe configuration
    - Initial service availability checks
    - Applications with slow startup times
    
    Returns:
        Startup status ({"status": "ready"})
        
    Raises:
        HTTPException 503: Service not started
        
    Logs:
        DEBUG: Startup checks
        INFO: Successful startup completion
        ERROR: Startup failures
    """
    try:
        logger.debug("Processing startup probe")
        
        # Basic initialization check (can query config)
        streams = await service.list_streams()
        
        logger.info(f"Startup check passed: service initialized with {len(streams)} stream(s)")
        
        return {"status": "ready"}
        
    except Exception as e:
        logger.error(f"Startup check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not started"
        )


# Log health check router initialization
logger.debug("Health check endpoints registered")
