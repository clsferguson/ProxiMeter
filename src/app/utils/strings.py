"""String utility functions for ProxiMeter."""
from __future__ import annotations

import re
from typing import Optional


def mask_rtsp_credentials(rtsp_url: str) -> str:
    """Mask credentials in RTSP URL for safe display/logging.
    
    Replaces username:password in rtsp://user:pass@host/path with ***:***
    
    Args:
        rtsp_url: RTSP URL that may contain credentials
        
    Returns:
        RTSP URL with credentials masked
        
    Examples:
        >>> mask_rtsp_credentials("rtsp://admin:secret@192.168.1.100/stream")
        'rtsp://***:***@192.168.1.100/stream'
        >>> mask_rtsp_credentials("rtsp://192.168.1.100/stream")
        'rtsp://192.168.1.100/stream'
    """
    if not rtsp_url:
        return rtsp_url
    
    # Pattern to match rtsp://username:password@host
    # Captures: protocol, username, password, host/path
    pattern = r'^(rtsp://)[^:@]+:[^@]+@(.+)$'
    
    match = re.match(pattern, rtsp_url, re.IGNORECASE)
    if match:
        protocol = match.group(1)
        host_and_path = match.group(2)
        return f"{protocol}***:***@{host_and_path}"
    
    # No credentials found, return as-is
    return rtsp_url


def normalize_stream_name(name: str) -> str:
    """Normalize stream name for comparison (trim whitespace, lowercase).
    
    Args:
        name: Stream name to normalize
        
    Returns:
        Normalized stream name
    """
    if not name:
        return ""
    return name.strip().lower()
