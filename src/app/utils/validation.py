"""Input validation utilities for ProxiMeter."""
from __future__ import annotations

import re
from typing import Final, Literal
from urllib.parse import urlparse, ParseResult
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

# Stream name constraints
STREAM_NAME_MIN_LENGTH: Final[int] = 1
STREAM_NAME_MAX_LENGTH: Final[int] = 50

# Zone name constraints
ZONE_NAME_MIN_LENGTH: Final[int] = 1
ZONE_NAME_MAX_LENGTH: Final[int] = 50

# Polygon constraints
MIN_POLYGON_POINTS: Final[int] = 3

# Valid protocols
VALID_RTSP_SCHEMES: Final[set[str]] = {"rtsp", "rtsps"}

# Valid ports
MIN_PORT: Final[int] = 1
MAX_PORT: Final[int] = 65535


# ============================================================================
# Result Types
# ============================================================================

ValidationResult = tuple[bool, str | None]


# ============================================================================
# RTSP URL Validation
# ============================================================================

def validate_rtsp_url(url: str) -> ValidationResult:
    """Validate RTSP URL format.
    
    Validates that:
    - URL starts with rtsp:// or rtsps:// (case-insensitive)
    - Host/IP address is non-empty and valid
    - Port is within valid range if specified
    - URL is properly formatted
    
    Args:
        url: RTSP URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, None)
        - If invalid: (False, error_description)
        
    Examples:
        >>> validate_rtsp_url("rtsp://192.168.1.100/stream")
        (True, None)
        >>> validate_rtsp_url("rtsp://admin:pass@cam.local:554/live")
        (True, None)
        >>> validate_rtsp_url("http://example.com")
        (False, "URL must use rtsp:// or rtsps:// scheme")
        >>> validate_rtsp_url("rtsp:///stream")
        (False, "Host cannot be empty")
    """
    if not url or not isinstance(url, str):
        return False, "RTSP URL is required and must be a string"
    
    # Check protocol
    url_lower = url.lower()
    if not any(url_lower.startswith(f"{scheme}://") for scheme in VALID_RTSP_SCHEMES):
        return False, "URL must use rtsp:// or rtsps:// scheme"
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        logger.warning(f"URL parsing failed for '{url}': {e}")
        return False, f"Invalid URL format: {str(e)}"
    
    # Validate scheme
    if parsed.scheme.lower() not in VALID_RTSP_SCHEMES:
        return False, f"Invalid scheme '{parsed.scheme}', must be rtsp or rtsps"
    
    # Validate host
    if not parsed.hostname:
        return False, "Host cannot be empty"
    
    # Validate hostname format (basic check)
    if not _is_valid_hostname(parsed.hostname):
        return False, f"Invalid hostname format: {parsed.hostname}"
    
    # Validate port if specified
    if parsed.port is not None:
        if not (MIN_PORT <= parsed.port <= MAX_PORT):
            return False, f"Port must be between {MIN_PORT} and {MAX_PORT}"
    
    return True, None


def _is_valid_hostname(hostname: str) -> bool:
    """Check if hostname is valid format (IP or domain).
    
    Args:
        hostname: Hostname to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Check for valid IP address
    if _is_valid_ip(hostname):
        return True
    
    # Check for valid domain name
    if _is_valid_domain(hostname):
        return True
    
    return False


def _is_valid_ip(ip: str) -> bool:
    """Check if string is a valid IPv4 or IPv6 address.
    
    Args:
        ip: IP address string
        
    Returns:
        True if valid IP, False otherwise
    """
    # IPv4 pattern
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ipv4_pattern, ip):
        # Validate octets are 0-255
        try:
            return all(0 <= int(octet) <= 255 for octet in ip.split('.'))
        except ValueError:
            return False
    
    # IPv6 pattern (simplified)
    ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
    if re.match(ipv6_pattern, ip):
        return True
    
    return False


def _is_valid_domain(domain: str) -> bool:
    """Check if string is a valid domain name.
    
    Args:
        domain: Domain name string
        
    Returns:
        True if valid domain, False otherwise
    """
    # Domain name pattern (RFC 1035)
    domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
    
    if not domain or len(domain) > 253:
        return False
    
    return bool(re.match(domain_pattern, domain))


# ============================================================================
# Stream Name Validation
# ============================================================================

def validate_stream_name(
    name: str,
    min_length: int = STREAM_NAME_MIN_LENGTH,
    max_length: int = STREAM_NAME_MAX_LENGTH
) -> ValidationResult:
    """Validate stream name.
    
    Validates that:
    - Name is not empty after trimming whitespace
    - Name length is within configured bounds
    - Name doesn't contain invalid characters
    
    Args:
        name: Stream name to validate
        min_length: Minimum allowed length (default: 1)
        max_length: Maximum allowed length (default: 50)
        
    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, None)
        - If invalid: (False, error_description)
        
    Examples:
        >>> validate_stream_name("Camera 1")
        (True, None)
        >>> validate_stream_name("")
        (False, "Stream name is required")
        >>> validate_stream_name("   ")
        (False, "Stream name cannot be empty or whitespace only")
    """
    if not name or not isinstance(name, str):
        return False, "Stream name is required and must be a string"
    
    trimmed = name.strip()
    
    if not trimmed:
        return False, "Stream name cannot be empty or whitespace only"
    
    if len(trimmed) < min_length:
        return False, f"Stream name must be at least {min_length} character(s)"
    
    if len(trimmed) > max_length:
        return False, f"Stream name must be at most {max_length} characters"
    
    # Check for control characters
    if any(ord(char) < 32 for char in trimmed):
        return False, "Stream name cannot contain control characters"
    
    return True, None


# ============================================================================
# Zone Name Validation
# ============================================================================

def validate_zone_name(
    name: str,
    min_length: int = ZONE_NAME_MIN_LENGTH,
    max_length: int = ZONE_NAME_MAX_LENGTH
) -> ValidationResult:
    """Validate zone name.
    
    Validates that:
    - Name is not empty after trimming whitespace
    - Name length is within configured bounds
    - Name doesn't contain invalid characters
    
    Args:
        name: Zone name to validate
        min_length: Minimum allowed length (default: 1)
        max_length: Maximum allowed length (default: 50)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name or not isinstance(name, str):
        return False, "Zone name is required and must be a string"
    
    trimmed = name.strip()
    
    if not trimmed:
        return False, "Zone name cannot be empty or whitespace only"
    
    if len(trimmed) < min_length:
        return False, f"Zone name must be at least {min_length} character(s)"
    
    if len(trimmed) > max_length:
        return False, f"Zone name must be at most {max_length} characters"
    
    # Check for control characters
    if any(ord(char) < 32 for char in trimmed):
        return False, "Zone name cannot contain control characters"
    
    return True, None


# ============================================================================
# Polygon Coordinate Validation
# ============================================================================

def validate_polygon_coordinates(
    coordinates: list[list[float]],
    min_points: int = MIN_POLYGON_POINTS
) -> ValidationResult:
    """Validate polygon coordinates for zone detection.
    
    Validates that:
    - Coordinates list has at least min_points points
    - Each point is a list/tuple of 2 numbers [x, y]
    - All coordinates are valid numbers (not NaN or infinity)
    - Coordinates are normalized (0.0 to 1.0)
    
    Args:
        coordinates: List of [x, y] coordinate pairs
        min_points: Minimum number of points (default: 3 for triangle)
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_polygon_coordinates([[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]])
        (True, None)
        >>> validate_polygon_coordinates([[0.1, 0.1], [0.9, 0.1]])
        (False, "Polygon must have at least 3 points")
    """
    if not isinstance(coordinates, list):
        return False, "Coordinates must be a list"
    
    if len(coordinates) < min_points:
        return False, f"Polygon must have at least {min_points} points"
    
    for idx, point in enumerate(coordinates):
        # Check point structure
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return False, f"Point {idx} must be a list/tuple of [x, y]"
        
        # Validate x and y coordinates
        try:
            x, y = float(point[0]), float(point[1])
        except (TypeError, ValueError):
            return False, f"Point {idx} coordinates must be numbers"
        
        # Check for NaN or infinity
        if not (float('-inf') < x < float('inf')):
            return False, f"Point {idx} x-coordinate is not a valid number"
        if not (float('-inf') < y < float('inf')):
            return False, f"Point {idx} y-coordinate is not a valid number"
        
        # Check normalized range (0.0 to 1.0)
        if not (0.0 <= x <= 1.0):
            return False, f"Point {idx} x-coordinate must be between 0.0 and 1.0 (got {x})"
        if not (0.0 <= y <= 1.0):
            return False, f"Point {idx} y-coordinate must be between 0.0 and 1.0 (got {y})"
    
    return True, None


# ============================================================================
# Utility Functions
# ============================================================================

def validate_all(validators: list[ValidationResult]) -> ValidationResult:
    """Combine multiple validation results.
    
    Returns (True, None) only if all validations passed.
    Otherwise returns first error.
    
    Args:
        validators: List of validation results
        
    Returns:
        Combined validation result
    """
    for is_valid, error in validators:
        if not is_valid:
            return False, error
    return True, None
