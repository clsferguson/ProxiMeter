"""Health check endpoints for service monitoring.

Provides health check endpoints for:
- Comprehensive health status with stream validation
- Simple alive check for monitoring systems

Health Status Levels:
    - healthy: All streams operational (or no streams configured)
    - degraded: Some streams have errors but service is functional
    - unhealthy: Critical service failure

Logging Strategy:
    DEBUG - Health check calls, stream validation details
    INFO  - Service initialization confirmation
    WARN  - Degraded status, specific stream errors
    ERROR - Health check failures, critical errors

Usage:
    # Full health check with stream validation
    >>> GET /health
    {
        "status": "healthy",
        "gpu_backend": "nvidia",
        "streams": [...],
        "metrics": {"total": 5, "active": 3, "stopped": 2, "errors": 0}
    }
    
    # Quick alive check
    >>> GET /health/live
    {"status": "alive"}
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List, Literal
import logging

from ..services import container
from ..services.streams_service import StreamsService
from ..config_io import get_gpu_backend

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Type aliases for better readability and type safety
HealthStatus = Literal["healthy", "degraded", "unhealthy"]
ProbeStatus = Literal["alive"]


def get_streams_service() -> StreamsService:
    """Dependency injection for streams service.
    
    Returns singleton StreamsService instance for health checks.
    
    Returns:
        StreamsService instance
        
    Raises:
        RuntimeError: If service not initialized (startup failed)
        
    Logs:
        DEBUG: Service injection
    """
    logger.debug("Injecting StreamsService for health check")
    
    if container.streams_service is None:
        logger.error("StreamsService not initialized - application startup may have failed")
        raise RuntimeError("StreamsService not initialized")
    
    return container.streams_service


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


async def calculate_health_status(
    streams: List[dict],
    service: StreamsService
) -> tuple[HealthStatus, List[str]]:
    """Calculate overall health status by validating stream operational state.
    
    Performs deep health check by:
    1. Verifying FFmpeg processes exist for running streams
    2. Checking if processes are still alive
    3. Attempting to read frames to confirm streams are working
    
    Health levels:
    - healthy: All streams working (or no streams configured)
    - degraded: Some streams have errors but service functional
    - unhealthy: Critical service failure (reserved for future use)
    
    Args:
        streams: List of stream configurations
        service: StreamsService instance for frame validation
        
    Returns:
        Tuple of (overall_status, list_of_error_messages)
        
    Logs:
        DEBUG: Health calculation details, validation steps
        WARN: Individual stream errors detected
    """
    if not streams:
        logger.debug("No streams configured, status: healthy")
        return "healthy", []
    
    errors: List[str] = []
    
    # Validate each stream that claims to be running
    for stream in streams:
        stream_id = stream.get("id")
        stream_name = stream.get("name", "Unknown")
        stream_status = stream.get("status", "stopped")
        
        # Skip stopped streams (intentional user action)
        if stream_status == "stopped":
            logger.debug(f"Stream {stream_name} ({stream_id}): stopped (intentional)")
            continue
        
        # Validate running streams
        if stream_status == "running":
            logger.debug(f"Validating running stream: {stream_name} ({stream_id})")
            
            # Check 1: Verify FFmpeg process exists
            if stream_id not in service.active_processes:
                error_msg = f"{stream_name}: Running but no FFmpeg process found"
                logger.warning(f"Health check failed: {error_msg}")
                errors.append(error_msg)
                continue
            
            proc_data = service.active_processes[stream_id]
            process = proc_data.get("process")
            
            # Check 2: Verify process is still alive
            if process and process.returncode is not None:
                error_msg = f"{stream_name}: FFmpeg process died (exit code {process.returncode})"
                logger.warning(f"Health check failed: {error_msg}")
                errors.append(error_msg)
                continue
            
            # Check 3: Verify stream is producing frames
            try:
                logger.debug(f"Attempting frame read for {stream_name}")
                frame_result = await service.get_frame(stream_id)
                
                if frame_result is None:
                    error_msg = f"{stream_name}: Unable to read frames (stream ended)"
                    logger.warning(f"Health check failed: {error_msg}")
                    errors.append(error_msg)
                elif isinstance(frame_result, tuple) and not frame_result[0]:
                    error_msg = f"{stream_name}: Frame extraction failed"
                    logger.warning(f"Health check failed: {error_msg}")
                    errors.append(error_msg)
                else:
                    logger.debug(f"Stream {stream_name}: frame validation passed")
                    
            except Exception as e:
                error_msg = f"{stream_name}: Frame check error: {str(e)}"
                logger.warning(f"Health check failed: {error_msg}")
                errors.append(error_msg)
    
    # Determine overall status
    if not errors:
        logger.debug(f"All {len(streams)} stream(s) operational, status: healthy")
        return "healthy", []
    else:
        logger.warning(
            f"{len(errors)} stream error(s) detected, status: degraded "
            f"({len(streams) - len(errors)}/{len(streams)} streams working)"
        )
        return "degraded", errors


# ============================================================================
# Health Check Endpoints
# ============================================================================

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(
    service: StreamsService = Depends(get_streams_service)
) -> Dict[str, Any]:
    """Comprehensive health check with stream validation.
    
    Returns detailed health information including:
    - Overall service status (healthy/degraded/unhealthy)
    - Individual stream statuses and acceleration modes
    - Active and total stream counts
    - GPU backend information
    - Specific error messages if degraded
    
    This endpoint performs deep validation by actually attempting to read
    frames from running streams to confirm they're operational.
    
    Returns:
        Health status dictionary with full metrics
        
    Raises:
        HTTPException 503: Critical service failure
        
    Example Response (Healthy):
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
                "errors": 0
            }
        }
        
    Example Response (Degraded):
        {
            "status": "degraded",
            "gpu_backend": "nvidia",
            "streams": [...],
            "metrics": {
                "total": 5,
                "active": 3,
                "stopped": 1,
                "errors": 1
            },
            "errors": [
                "Camera 2: FFmpeg process died (exit code 1)"
            ]
        }
        
    Logs:
        DEBUG: Health check invocation, stream validation details
        WARN: Degraded status with error details
        ERROR: Health check failures, exceptions
    """
    try:
        logger.debug("Processing comprehensive health check")
        
        # Gather stream configurations
        streams = await service.list_streams()
        gpu_backend = get_gpu_backend()
        
        logger.debug(f"Retrieved {len(streams)} stream(s) for health validation")
        
        # Calculate actual health by validating stream operation
        overall_status, error_messages = await calculate_health_status(streams, service)
        
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
        active_count = sum(1 for s in streams if s.get("status") == "running")
        stopped_count = sum(1 for s in streams if s.get("status") == "stopped")
        
        # Build response
        response = {
            "status": overall_status,
            "gpu_backend": gpu_backend,
            "streams": stream_details,
            "metrics": {
                "total": len(streams),
                "active": active_count,
                "stopped": stopped_count,
                "errors": len(error_messages)
            }
        }
        
        # Add error details if present
        if error_messages:
            response["errors"] = error_messages
        
        # Log health status
        if overall_status == "degraded":
            logger.warning(
                f"Health check: {overall_status} - {len(error_messages)} error(s), "
                f"{active_count}/{len(streams)} streams active"
            )
            # Log each specific error
            for error in error_messages:
                logger.warning(f"  - {error}")
                
        elif overall_status == "unhealthy":
            logger.error(f"Health check: {overall_status} - Service not functional")
            
        else:
            logger.debug(
                f"Health check: {overall_status} - "
                f"{active_count}/{len(streams)} streams active, {len(error_messages)} errors"
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Health check failed with exception: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, ProbeStatus]:
    """Simple liveness check for monitoring systems.
    
    Returns immediately to verify the service process is running and
    responsive. Does not check dependencies or stream functionality.
    
    Use this for:
    - Docker healthcheck directive
    - Uptime monitoring (Uptime Kuma, Pingdom, etc.)
    - Load balancer health checks
    - High-frequency monitoring (low overhead)
    
    Returns:
        Liveness status (always {"status": "alive"})
        
    Logs:
        DEBUG: Liveness check calls
    """
    logger.debug("Liveness check called")
    return {"status": "alive"}


# Log health check router initialization
logger.debug("Health check endpoints registered: /health, /health/live")