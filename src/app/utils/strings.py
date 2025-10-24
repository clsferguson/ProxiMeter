"""String manipulation and formatting utilities for ProxiMeter."""
from __future__ import annotations

import re
import unicodedata
from typing import Final
from urllib.parse import urlparse, urlunparse

# ============================================================================
# Constants
# ============================================================================

# RTSP credential masking pattern
RTSP_CREDENTIALS_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'^(rtsps?://)([^:@]+):([^@]+)@(.+)$',
    re.IGNORECASE
)

# Mask placeholder
CREDENTIALS_MASK: Final[str] = "***:***"


# ============================================================================
# Credential Masking
# ============================================================================

def mask_rtsp_credentials(rtsp_url: str) -> str:
    """Mask credentials in RTSP URL for safe display and logging.
    
    Replaces username:password in rtsp://user:pass@host/path with ***:***
    while preserving the rest of the URL structure.
    
    Security Note:
        This function should be called before logging or displaying RTSP URLs
        to prevent credential leakage in logs, error messages, or UI.
    
    Args:
        rtsp_url: RTSP URL that may contain embedded credentials
        
    Returns:
        RTSP URL with credentials replaced by masked placeholder
        
    Examples:
        >>> mask_rtsp_credentials("rtsp://admin:secret@192.168.1.100/stream")
        'rtsp://***:***@192.168.1.100/stream'
        
        >>> mask_rtsp_credentials("rtsp://192.168.1.100/stream")
        'rtsp://192.168.1.100/stream'
        
        >>> mask_rtsp_credentials("rtsps://user:pass123@cam.local:8554/live")
        'rtsps://***:***@cam.local:8554/live'
    """
    if not rtsp_url or not isinstance(rtsp_url, str):
        return rtsp_url
    
    match = RTSP_CREDENTIALS_PATTERN.match(rtsp_url)
    if match:
        protocol = match.group(1)  # rtsp:// or rtsps://
        # username = match.group(2)  # Not used, just captured
        # password = match.group(3)  # Not used, just captured
        host_and_path = match.group(4)
        return f"{protocol}{CREDENTIALS_MASK}@{host_and_path}"
    
    # No credentials found, return unchanged
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
    """Normalize stream name for case-insensitive comparison.
    
    Performs:
    - Whitespace trimming
    - Lowercase conversion
    - Unicode normalization (NFC)
    
    Args:
        name: Stream name to normalize
        
    Returns:
        Normalized stream name for comparison
        
    Examples:
        >>> normalize_stream_name("  Camera 1  ")
        'camera 1'
        
        >>> normalize_stream_name("Front Door")
        'front door'
    """
    if not name or not isinstance(name, str):
        return ""
    
    # Trim whitespace and lowercase
    normalized = name.strip().lower()
    
    # Unicode normalization (combine diacritics)
    normalized = unicodedata.normalize('NFC', normalized)
    
    return normalized


def normalize_zone_name(name: str) -> str:
    """Normalize zone name for case-insensitive comparison.
    
    Performs:
    - Whitespace trimming
    - Lowercase conversion
    - Unicode normalization (NFC)
    
    Args:
        name: Zone name to normalize
        
    Returns:
        Normalized zone name for comparison
    """
    if not name or not isinstance(name, str):
        return ""
    
    normalized = name.strip().lower()
    normalized = unicodedata.normalize('NFC', normalized)
    
    return normalized


# ============================================================================
# String Sanitization
# ============================================================================

def sanitize_for_filename(text: str, max_length: int = 50) -> str:
    """Sanitize string for safe use in filenames.
    
    Removes or replaces characters that are problematic in filenames:
    - Replaces spaces with underscores
    - Removes special characters
    - Truncates to max_length
    
    Args:
        text: Text to sanitize
        max_length: Maximum filename length (default: 50)
        
    Returns:
        Sanitized string safe for filenames
        
    Examples:
        >>> sanitize_for_filename("Front Door Camera!")
        'front_door_camera'
        
        >>> sanitize_for_filename("Stream #1 (Main)")
        'stream_1_main'
    """
    if not text:
        return "unnamed"
    
    # Lowercase and normalize
    text = text.lower().strip()
    text = unicodedata.normalize('NFKD', text)
    
    # Remove non-ASCII characters
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Replace spaces with underscores
    text = text.replace(' ', '_')
    
    # Remove special characters (keep only alphanumeric and underscores)
    text = re.sub(r'[^a-z0-9_]', '', text)
    
    # Remove consecutive underscores
    text = re.sub(r'_+', '_', text)
    
    # Trim underscores from ends
    text = text.strip('_')
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length].rstrip('_')
    
    return text or "unnamed"


def sanitize_log_message(message: str) -> str:
    """Sanitize message for logging by masking credentials.
    
    Args:
        message: Log message that may contain sensitive data
        
    Returns:
        Sanitized message with credentials masked
    """
    if not message:
        return message
    
    # Mask RTSP credentials
    message = RTSP_CREDENTIALS_PATTERN.sub(
        r'\1***:***@\4',
        message
    )
    
    return message


# ============================================================================
# String Formatting
# ============================================================================

def format_bytes(size_bytes: int | float) -> str:
    """Format bytes into human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB", "2.3 GB")
        
    Examples:
        >>> format_bytes(1024)
        '1.0 KB'
        
        >>> format_bytes(1536)
        '1.5 KB'
        
        >>> format_bytes(1048576)
        '1.0 MB'
    """
    if size_bytes < 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def format_duration(seconds: int | float) -> str:
    """Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "1h 30m", "45s")
        
    Examples:
        >>> format_duration(45)
        '45s'
        
        >>> format_duration(90)
        '1m 30s'
        
        >>> format_duration(3665)
        '1h 1m 5s'
    """
    if seconds < 0:
        return "0s"
    
    seconds = int(seconds)
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append if truncated (default: "...")
        
    Returns:
        Truncated string
        
    Examples:
        >>> truncate_string("This is a long string", 10)
        'This is...'
        
        >>> truncate_string("Short", 10)
        'Short'
    """
    if not text or len(text) <= max_length:
        return text
    
    if max_length <= len(suffix):
        return suffix[:max_length]
    
    return text[:max_length - len(suffix)] + suffix


# ============================================================================
# URL Manipulation
# ============================================================================

def build_rtsp_url(
    host: str,
    port: int | None = None,
    path: str = "/",
    username: str | None = None,
    password: str | None = None,
    secure: bool = False
) -> str:
    """Build RTSP URL from components.
    
    Args:
        host: Hostname or IP address
        port: Port number (optional, uses default 554)
        path: Path component (default: "/")
        username: Username for authentication (optional)
        password: Password for authentication (optional)
        secure: Use rtsps:// instead of rtsp:// (default: False)
        
    Returns:
        Constructed RTSP URL
        
    Examples:
        >>> build_rtsp_url("192.168.1.100", path="/stream")
        'rtsp://192.168.1.100/stream'
        
        >>> build_rtsp_url("cam.local", port=8554, username="admin", password="pass")
        'rtsp://admin:pass@cam.local:8554/'
    """
    scheme = "rtsps" if secure else "rtsp"
    
    # Build netloc with optional authentication and port
    if username and password:
        netloc = f"{username}:{password}@{host}"
    else:
        netloc = host
    
    if port:
        netloc = f"{netloc}:{port}"
    
    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path
    
    return urlunparse((scheme, netloc, path, '', '', ''))
