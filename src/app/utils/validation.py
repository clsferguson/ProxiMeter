"""Input validation utilities.

Provides validation functions for:
- RTSP URL format and structure
- Hostname/IP validation
- Port range validation

Note on Logging:
    These are pure validation functions that return (bool, error_message).
    Only logs when URL parsing fails (unexpected). Most validation failures
    return descriptive error messages to the caller who decides how to log.

Note on Pydantic:
    Stream/zone names and polygon coordinates are validated by Pydantic models.
    This module only handles RTSP URL validation which requires complex logic.
"""
from __future__ import annotations

import re
import logging
from typing import Final
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

VALID_RTSP_SCHEMES: Final[set[str]] = {"rtsp", "rtsps"}
"""Valid RTSP URL schemes."""

MIN_PORT: Final[int] = 1
MAX_PORT: Final[int] = 65535
"""Valid TCP/UDP port range."""

# Type alias for validation results
ValidationResult = tuple[bool, str | None]
"""Validation result: (is_valid, error_message)"""

# ============================================================================
# RTSP URL Validation
# ============================================================================

def validate_rtsp_url(url: str) -> ValidationResult:
    """Validate RTSP URL format and structure.
    
    Checks:
    - Scheme is rtsp:// or rtsps:// (case-insensitive)
    - Host/IP is non-empty and valid
    - Port is in valid range if specified
    - URL is properly formatted
    
    Args:
        url: RTSP URL to validate
        
    Returns:
        (True, None) if valid
        (False, error_message) if invalid
        
    Examples:
        >>> validate_rtsp_url("rtsp://192.168.1.100/stream")
        (True, None)
        
        >>> validate_rtsp_url("http://example.com")
        (False, "URL must use rtsp:// or rtsps:// scheme")
        
        >>> validate_rtsp_url("rtsp:///stream")
        (False, "Host cannot be empty")
    """
    if not url or not isinstance(url, str):
        return False, "RTSP URL is required and must be a string"
    
    # Check scheme
    url_lower = url.lower()
    if not any(url_lower.startswith(f"{scheme}://") for scheme in VALID_RTSP_SCHEMES):
        return False, "URL must use rtsp:// or rtsps:// scheme"
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        logger.warning(f"URL parse error: {e}")
        return False, f"Invalid URL format: {str(e)}"
    
    # Validate scheme (redundant but thorough)
    if parsed.scheme.lower() not in VALID_RTSP_SCHEMES:
        return False, f"Invalid scheme '{parsed.scheme}'"
    
    # Validate host
    if not parsed.hostname:
        return False, "Host cannot be empty"
    
    # Validate hostname format
    if not _is_valid_hostname(parsed.hostname):
        return False, f"Invalid hostname: {parsed.hostname}"
    
    # Validate port if specified
    if parsed.port is not None:
        if not (MIN_PORT <= parsed.port <= MAX_PORT):
            return False, f"Port must be {MIN_PORT}-{MAX_PORT}"
    
    return True, None


# ============================================================================
# Hostname Validation
# ============================================================================

def _is_valid_hostname(hostname: str) -> bool:
    """Check if hostname is valid IP or domain.
    
    Args:
        hostname: Hostname to validate
        
    Returns:
        True if valid IP or domain
    """
    return _is_valid_ip(hostname) or _is_valid_domain(hostname)


def _is_valid_ip(ip: str) -> bool:
    """Check if string is valid IPv4 or IPv6 address.
    
    Args:
        ip: IP address string
        
    Returns:
        True if valid IP
    """
    # IPv4: 0.0.0.0 to 255.255.255.255
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ipv4_pattern, ip):
        try:
            return all(0 <= int(octet) <= 255 for octet in ip.split('.'))
        except ValueError:
            return False
    
    # IPv6: simplified pattern
    ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
    return bool(re.match(ipv6_pattern, ip))


def _is_valid_domain(domain: str) -> bool:
    """Check if string is valid domain name (RFC 1035).
    
    Args:
        domain: Domain name string
        
    Returns:
        True if valid domain
    """
    if not domain or len(domain) > 253:
        return False
    
    # RFC 1035: labels separated by dots, 63 chars max per label
    domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
    return bool(re.match(domain_pattern, domain))


logger.debug("Validation utilities module loaded")
