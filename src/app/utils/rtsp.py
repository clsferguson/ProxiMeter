"""RTSP utilities for playback and frame generation."""
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


async def generate_mjpeg_stream(rtsp_url: str, max_fps: float = 5.0) -> AsyncGenerator[bytes, None]:
    """Generate MJPEG frames from RTSP stream at specified FPS cap.
    
    Args:
        rtsp_url: RTSP URL to decode
        max_fps: Maximum frames per second (default 5.0)
        
    Yields:
        JPEG frame bytes with multipart boundary
        
    Raises:
        RuntimeError: If stream cannot be opened or fails during playback
    """
    # TODO: Implement in T030
    logger.warning(f"MJPEG generator not yet implemented for {rtsp_url}")
    raise NotImplementedError("MJPEG stream generation not yet implemented")


async def probe_rtsp_stream(rtsp_url: str, timeout_seconds: float = 2.0) -> bool:
    """Probe RTSP stream to check connectivity.
    
    Attempts to read a single frame to verify the stream is reachable.
    
    Args:
        rtsp_url: RTSP URL to probe
        timeout_seconds: Timeout for probe attempt (default 2.0)
        
    Returns:
        True if stream is reachable, False otherwise
    """
    # TODO: Implement in T028
    logger.warning(f"RTSP probe not yet implemented for {rtsp_url}")
    return False
