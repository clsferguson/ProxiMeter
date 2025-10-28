"""Service container for singleton instances.

This module holds global service instances to avoid circular imports.
It's imported by both main.py and api modules.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .streams_service import StreamsService

# Global singleton instance
streams_service: "StreamsService | None" = None


def get_streams_service() -> "StreamsService":
    """Get the global StreamsService singleton instance.
    
    This dependency is injected into all API route handlers.
    
    Returns:
        The global StreamsService instance
        
    Raises:
        RuntimeError: If called before application startup
    """
    if streams_service is None:
        raise RuntimeError(
            "StreamsService not initialized. "
            "Application startup may have failed."
        )
    return streams_service