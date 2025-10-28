"""Service container for singleton instances.

Holds global service instances to break circular import dependencies.
Pattern: main.py initializes services → container stores them → API imports them

Why This Exists:
    Without this module, we'd have a circular dependency:
    - main.py imports api/streams.py (to register routes)
    - api/streams.py imports StreamsService
    - StreamsService might import from main.py
    
    The container breaks this cycle by providing a neutral storage point.

Critical Design Note:
    The singleton pattern ensures ALL API requests use the SAME StreamsService
    instance with the SAME active_processes dict. This is essential because:
    - start_stream() adds FFmpeg process to active_processes
    - get_frame() reads from active_processes
    - If different instances, they'd have different dicts = "process not found"

Logging Strategy:
    DEBUG - Service dependency injection
    ERROR - Service not initialized (critical failure)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .streams_service import StreamsService

logger = logging.getLogger(__name__)

# ============================================================================
# Global Singleton Instance
# ============================================================================

streams_service: StreamsService | None = None
"""Global StreamsService singleton initialized during app startup."""


# ============================================================================
# Dependency Injection
# ============================================================================

def get_streams_service() -> StreamsService:
    """Get the global StreamsService singleton for dependency injection.
    
    Used by FastAPI's Depends() in all API route handlers to ensure
    all requests use the same service instance.
    
    Returns:
        Global StreamsService instance
        
    Raises:
        RuntimeError: If called before app startup (service not initialized)
        
    Example:
        >>> @router.get("/streams")
        >>> async def list_streams(
        ...     service: StreamsService = Depends(get_streams_service)
        ... ):
        ...     return await service.list_streams()
    """
    if streams_service is None:
        logger.error("StreamsService dependency requested before initialization")
        raise RuntimeError(
            "StreamsService not initialized. "
            "Application startup may have failed."
        )
    
    logger.debug("Injecting StreamsService singleton")
    return streams_service


logger.debug("Service container module loaded")