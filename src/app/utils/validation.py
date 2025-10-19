"""Validation utilities for ProxiMeter."""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse


def validate_rtsp_url(url: str) -> tuple[bool, Optional[str]]:
    """Validate RTSP URL format.
    
    Checks that:
    - URL starts with rtsp:// (case-insensitive)
    - Host is non-empty
    - URL is properly formatted
    
    Args:
        url: RTSP URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is None
        If invalid, error_message describes the problem
        
    Examples:
        >>> validate_rtsp_url("rtsp://192.168.1.100/stream")
        (True, None)
        >>> validate_rtsp_url("http://example.com")
        (False, "URL must start with rtsp://")
        >>> validate_rtsp_url("rtsp:///stream")
        (False, "Host cannot be empty")
    """
    if not url:
        return False, "RTSP URL is required"
    
    # Check protocol
    if not url.lower().startswith("rtsp://"):
        return False, "URL must start with rtsp://"
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"
    
    # Check host is non-empty
    if not parsed.hostname:
        return False, "Host cannot be empty"
    
    return True, None


def validate_stream_name(name: str, min_length: int = 1, max_length: int = 50) -> tuple[bool, Optional[str]]:
    """Validate stream name.
    
    Checks that:
    - Name is not empty after trimming
    - Name length is within bounds
    
    Args:
        name: Stream name to validate
        min_length: Minimum allowed length (default: 1)
        max_length: Maximum allowed length (default: 50)
        
    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is None
        If invalid, error_message describes the problem
    """
    if not name:
        return False, "Stream name is required"
    
    trimmed = name.strip()
    
    if not trimmed:
        return False, "Stream name cannot be empty or whitespace only"
    
    if len(trimmed) < min_length:
        return False, f"Stream name must be at least {min_length} character(s)"
    
    if len(trimmed) > max_length:
        return False, f"Stream name must be at most {max_length} characters"
    
    return True, None
