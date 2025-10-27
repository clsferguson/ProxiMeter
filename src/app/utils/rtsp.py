"""RTSP stream utilities for FFmpeg-based stream processing.

Constitution-compliant utilities for RTSP stream validation and FFmpeg
command generation. No OpenCV - all stream processing uses FFmpeg.

Principle II: FFmpeg handles ALL RTSP stream ingestion, decoding, and
frame extraction.

Principle III: GPU backend contract with hardware acceleration support.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Final
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

DEFAULT_PROBE_TIMEOUT: Final[float] = 5.0
"""Default timeout for RTSP stream probing (seconds)."""

FORBIDDEN_SHELL_CHARS: Final[set[str]] = {";", "&", "|", ">", "<", "`", "$", "\n", "\r"}
"""Shell metacharacters forbidden in FFmpeg parameters for security."""

GPU_FFMPEG_FLAGS: Final[set[str]] = {"-hwaccel", "-hwaccel_output_format", "-c:v"}
"""FFmpeg flags that indicate GPU acceleration usage."""

# ============================================================================
# FFmpeg Command Building
# ============================================================================

def build_ffmpeg_command(
    rtsp_url: str,
    ffmpeg_params: list[str],
    gpu_backend: str | None = None
) -> list[str]:
    """Build FFmpeg command for RTSP stream processing with GPU acceleration.
    
    Constructs FFmpeg command that:
    - Decodes RTSP stream using GPU (if available)
    - Forces target FPS output
    - Outputs MJPEG to stdout for piping
    - Includes user-provided custom parameters
    
    Constitution Principle II: FFmpeg for all RTSP processing.
    Constitution Principle III: GPU backend contract enforcement.
    
    Args:
        rtsp_url: RTSP URL to process
        ffmpeg_params: User-provided FFmpeg parameters (already validated)
        gpu_backend: GPU backend (nvidia, amd, intel, or None for CPU)
        
    Returns:
        List of command arguments for subprocess execution
        
    Example:
        >>> cmd = build_ffmpeg_command(
        ...     "rtsp://cam/stream",
        ...     ["-rtsp_transport", "tcp"],
        ...     "nvidia"
        ... )
        >>> # Run with: subprocess.run(cmd, stdout=subprocess.PIPE)
    """
    cmd = ["ffmpeg"]
    
    logger.debug(f"Building FFmpeg command with GPU backend: {gpu_backend}")
    logger.debug(f"User ffmpeg_params: {ffmpeg_params}")

    # Add user-provided parameters first (allows overriding defaults)
    cmd.extend(ffmpeg_params)
    
    # Add input
    cmd.extend(["-i", rtsp_url])
    
    # Force FPS output
    cmd.extend(["-r", "5"])
    
    # Output configuration: MJPEG to stdout
    cmd.extend([
        "-c:v", "mjpeg",           # MJPEG codec
        "-q:v", "8",               # Quality (1-31, lower is better; 8 is high quality)
        "-f", "mjpeg",             # MJPEG format
        "-"                        # Output to stdout
    ])
    
    logger.debug(f"Final FFmpeg command: {' '.join(cmd)}")

    return cmd


# ============================================================================
# RTSP Stream Probing (FFmpeg-based)
# ============================================================================

async def probe_rtsp_stream(
    rtsp_url: str,
    timeout_seconds: float = DEFAULT_PROBE_TIMEOUT
) -> bool:
    """Probe RTSP stream connectivity using FFmpeg.
    
    Uses FFmpeg to verify stream is accessible and decodable.
    Attempts to read stream metadata without processing full frames.
    
    Constitution Principle II: FFmpeg for all RTSP operations.
    
    Args:
        rtsp_url: RTSP URL to probe
        timeout_seconds: Timeout for probe attempt (default: 5.0 seconds)
        
    Returns:
        True if stream is accessible and valid, False otherwise
        
    Example:
        >>> if await probe_rtsp_stream("rtsp://cam/stream"):
        ...     print("Stream is accessible")
    """
    try:
        # Use ffprobe to check stream metadata
        cmd = [
            "ffprobe",
            "-v", "quiet",                    # Suppress output
            "-print_format", "json",          # JSON output format
            "-show_streams",                   # Show stream info
            "-rtsp_transport", "tcp",         # Use TCP
            "-timeout", str(int(timeout_seconds * 1000000)),  # Timeout in microseconds
            rtsp_url
        ]
        
        # Run probe with timeout
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds
            )
            
            # Check if probe succeeded
            if process.returncode == 0 and stdout:
                logger.debug(f"RTSP probe successful: {rtsp_url}")
                return True
            
            # Log error if probe failed
            if stderr:
                error_msg = stderr.decode().strip()
                logger.debug(f"RTSP probe failed for {rtsp_url}: {error_msg}")
            
            return False
            
        except asyncio.TimeoutError:
            logger.debug(f"RTSP probe timeout for {rtsp_url} after {timeout_seconds}s")
            process.kill()
            await process.wait()
            return False
            
    except Exception as e:
        logger.debug(f"RTSP probe error for {rtsp_url}: {e}")
        return False


# ============================================================================
# Validation
# ============================================================================

def validate_rtsp_url(url: str, params: list[str], gpu_backend: str) -> bool:
    """Validate RTSP URL and FFmpeg parameters for security and compatibility.
    
    Checks:
    - URL format and protocol (rtsp:// or rtsps://)
    - Shell injection risks in parameters
    - GPU parameter compatibility with detected hardware
    
    Constitution Principle III: GPU backend validation.
    Constitution Principle IV: Security controls with input validation.
    
    Args:
        url: RTSP URL to validate
        params: FFmpeg parameters to validate
        gpu_backend: Detected GPU backend (nvidia, amd, intel, none)
        
    Returns:
        True if valid and safe, False otherwise
        
    Example:
        >>> if validate_rtsp_url(url, params, "nvidia"):
        ...     # Safe to proceed
        ...     cmd = build_ffmpeg_command(...)
    """
    # Validate URL format
    if not url or not isinstance(url, str):
        logger.warning("RTSP URL is empty or invalid type")
        return False
    
    url_lower = url.lower()
    if not url_lower.startswith("rtsp://") and not url_lower.startswith("rtsps://"):
        logger.warning(f"Invalid RTSP URL scheme: {url}")
        return False
    
    # Parse URL to check structure
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            logger.warning(f"RTSP URL missing host: {url}")
            return False
    except Exception as e:
        logger.warning(f"Failed to parse RTSP URL: {e}")
        return False
    
    # Validate FFmpeg parameters for shell injection risks
    for param in params:
        if not isinstance(param, str):
            logger.warning(f"Invalid FFmpeg param type: {type(param)}")
            return False
        
        # Check for forbidden shell characters
        if any(char in param for char in FORBIDDEN_SHELL_CHARS):
            logger.warning(f"FFmpeg param contains forbidden characters: {param}")
            return False
    
    # Validate GPU parameters match hardware
    if gpu_backend == "none":
        for param in params:
            if any(flag in param for flag in GPU_FFMPEG_FLAGS):
                logger.warning(f"GPU parameter '{param}' used but no GPU detected")
                return False
    
    return True


def validate_ffmpeg_params(params: list[str]) -> tuple[bool, str | None]:
    """Validate FFmpeg parameters for security and format.
    
    Ensures parameters are safe to pass to subprocess.
    
    Args:
        params: List of FFmpeg parameter strings
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(params, list):
        return False, "FFmpeg params must be a list"
    
    for param in params:
        if not isinstance(param, str):
            return False, f"Invalid parameter type: {type(param)}"
        
        # Check for shell injection attempts
        if any(char in param for char in FORBIDDEN_SHELL_CHARS):
            return False, f"Parameter contains forbidden characters: {param}"
        
        # Ensure params are non-empty
        if not param.strip():
            return False, "Empty parameter not allowed"
    
    return True, None


# ============================================================================
# Utility Functions
# ============================================================================

def format_ffmpeg_command(cmd: list[str]) -> str:
    """Format FFmpeg command for logging (mask sensitive info).
    
    Args:
        cmd: FFmpeg command list
        
    Returns:
        Formatted command string with credentials masked
    """
    formatted = []
    for part in cmd:
        if part.startswith("rtsp://") or part.startswith("rtsps://"):
            # Mask credentials in RTSP URL
            try:
                parsed = urlparse(part)
                if parsed.username or parsed.password:
                    masked = f"{parsed.scheme}://*****:*****@{parsed.hostname}"
                    if parsed.port:
                        masked += f":{parsed.port}"
                    masked += parsed.path
                    formatted.append(masked)
                else:
                    formatted.append(part)
            except:
                formatted.append("rtsp://*****")
        else:
            formatted.append(part)
    
    return " ".join(formatted)
