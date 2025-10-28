"""String manipulation and formatting utilities.

Provides utilities for:
- RTSP credential masking (security)
- String normalization (case-insensitive comparison)
- URL parsing and manipulation

Note on Logging:
    These are pure utility functions with no side effects or I/O.
    They don't require logging as they simply transform inputs to outputs.
    Callers log the results if needed.

Security:
    Always mask RTSP URLs before logging to prevent credential leakage.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Final
from urllib.parse import urlparse

# ============================================================================
# Constants
# ============================================================================

RTSP_CREDENTIALS_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'^(rtsps?://)([^:@]+):([^@]+)@(.+)$',
    re.IGNORECASE
)
"""Regex to match and extract RTSP credentials."""

CREDENTIALS_MASK: Final[str] = "***:***"
"""Placeholder for masked credentials."""

# ============================================================================
# Credential Masking
# ============================================================================

def mask_rtsp_credentials(rtsp_url: str) -> str:
    """Mask credentials in RTSP URL for safe logging and display.
    
    Replaces username:password with ***:*** while preserving URL structure.
    
    Security:
        ALWAYS call this before logging RTSP URLs to prevent credential
        leakage in logs, error messages, or UI.
    
    Args:
        rtsp_url: RTSP URL that may contain credentials
        
    Returns:
        URL with credentials masked
        
    Examples:
        >>> mask_rtsp_credentials("rtsp://admin:secret@192.168.1.100/stream")
        'rtsp://***:***@192.168.1.100/stream'
        
        >>> mask_rtsp_credentials("rtsp://192.168.1.100/stream")
        'rtsp://192.168.1.100/stream'
    """
    if not rtsp_url or not isinstance(rtsp_url, str):
        return rtsp_url
    
    match = RTSP_CREDENTIALS_PATTERN.match(rtsp_url)
    if match:
        protocol = match.group(1)  # rtsp:// or rtsps://
        host_and_path = match.group(4)  # everything after @
        return f"{protocol}{CREDENTIALS_MASK}@{host_and_path}"
    
    return rtsp_url


def extract_rtsp_host(rtsp_url: str) -> str | None:
    """Extract hostname/IP from RTSP URL.
    
    Args:
        rtsp_url: RTSP URL
        
    Returns:
        Hostname/IP or None if parsing fails
        
    Examples:
        >>> extract_rtsp_host("rtsp://admin:pass@192.168.1.100/stream")
        '192.168.1.100'
        
        >>> extract_rtsp_host("rtsp://cam.local:554/live")
        'cam.local'
    """
    try:
        parsed = urlparse(rtsp_url)
        return parsed.hostname
    except Exception:
        return None


# ============================================================================
# String Normalization
# ============================================================================

def normalize_stream_name(name: str) -> str:
    """Normalize stream/zone name for case-insensitive comparison.
    
    Operations:
    - Strip whitespace
    - Lowercase
    - Unicode normalization (NFC)
    
    Used for checking duplicate names across streams and zones.
    
    Args:
        name: Stream or zone name
        
    Returns:
        Normalized name for comparison
        
    Examples:
        >>> normalize_stream_name("  Camera 1  ")
        'camera 1'
        
        >>> normalize_stream_name("Front Door")
        'front door'
    """
    if not name or not isinstance(name, str):
        return ""
    
    # Trim and lowercase
    normalized = name.strip().lower()
    
    # Unicode normalization (combine diacritics)
    normalized = unicodedata.normalize('NFC', normalized)
    
    return normalized


# Alias for clarity (zones use same normalization as streams)
normalize_zone_name = normalize_stream_name
