"""RTSP stream utilities for FFmpeg-based processing.

FFmpeg-only utilities for RTSP stream validation and command generation.
No OpenCV VideoCapture - all stream processing uses FFmpeg with GPU acceleration.

Constitution Compliance:
    Principle II: FFmpeg handles ALL RTSP ingestion, decoding, frame extraction
    Principle III: GPU backend contract with hardware acceleration
    Principle IV: Security controls with input validation

Logging Strategy:
    DEBUG - Command building, probe results, validation details
    WARN  - Invalid URLs, security violations, GPU mismatches
    ERROR - Probe failures, exceptions

FFmpeg Pipeline:
    RTSP → FFmpeg (GPU decode) → MJPEG stdout → Parse frames → Web/API
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
"""Default RTSP probe timeout in seconds."""

FORBIDDEN_SHELL_CHARS: Final[set[str]] = {";", "&", "|", ">", "<", "`", "$", "\n", "\r"}
"""Shell metacharacters forbidden for security."""

# ============================================================================
# FFmpeg Command Building
# ============================================================================

def build_ffmpeg_command(
    rtsp_url: str,
    ffmpeg_params: list[str],
    gpu_backend: str | None = None
) -> list[str]:
    """Build FFmpeg command for RTSP processing with GPU acceleration.
    
    Command structure:
    1. User params (can override defaults)
    2. Input (-i rtsp://...)
    3. FPS limiter (-r 5)
    4. GPU download filter (if using GPU)
    5. MJPEG output to stdout
    
    Args:
        rtsp_url: RTSP URL to process
        ffmpeg_params: User-provided parameters (validated)
        gpu_backend: GPU backend (nvidia/amd/intel/none)
        
    Returns:
        Command list for subprocess.run()
        
    Example:
        >>> cmd = build_ffmpeg_command(
        ...     "rtsp://cam/stream",
        ...     ["-rtsp_transport", "tcp"],
        ...     "nvidia"
        ... )
    """
    cmd = ["ffmpeg"]
    
    logger.debug(f"Building FFmpeg command: GPU={gpu_backend}, params={len(ffmpeg_params)}")
    
    # User params first (allows override)
    cmd.extend(ffmpeg_params)
    
    # Input
    cmd.extend(["-i", rtsp_url])
    
    # Force 5fps output (constitution requirement)
    cmd.extend(["-r", "5"])
    
    # GPU download filter if using hardware acceleration
    if gpu_backend and gpu_backend != "none":
        cmd.extend(["-vf", "hwdownload,format=nv12"])
        logger.debug(f"Added GPU download filter for {gpu_backend}")
    
    # MJPEG output to stdout
    cmd.extend([
        "-c:v", "mjpeg",
        "-q:v", "8",  # Quality 8 (high quality, 1-31 scale)
        "-f", "mjpeg",
        "-"  # stdout
    ])
    
    return cmd


# ============================================================================
# RTSP Stream Probing
# ============================================================================

async def probe_rtsp_stream(
    rtsp_url: str,
    timeout_seconds: float = DEFAULT_PROBE_TIMEOUT
) -> bool:
    """Probe RTSP stream connectivity using ffprobe.
    
    Verifies stream is accessible and decodable without processing frames.
    
    Args:
        rtsp_url: RTSP URL to probe
        timeout_seconds: Probe timeout (default: 5.0)
        
    Returns:
        True if accessible, False otherwise
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-rtsp_transport", "tcp",
            "-timeout", str(int(timeout_seconds * 1000000)),  # microseconds
            rtsp_url
        ]
        
        logger.debug(f"Probing RTSP stream: {rtsp_url}")
        
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
            
            if process.returncode == 0 and stdout:
                logger.debug(f"Probe successful: {rtsp_url}")
                return True
            
            if stderr:
                error_msg = stderr.decode().strip()
                logger.debug(f"Probe failed: {error_msg}")
            
            return False
            
        except asyncio.TimeoutError:
            logger.debug(f"Probe timeout after {timeout_seconds}s")
            process.kill()
            await process.wait()
            return False
            
    except Exception as e:
        logger.debug(f"Probe error: {e}")
        return False


# ============================================================================
# Validation
# ============================================================================

def validate_rtsp_url(url: str, params: list[str], gpu_backend: str) -> bool:
    """Validate RTSP URL and FFmpeg params for security and compatibility.
    
    Checks:
    - URL format and protocol (rtsp:// or rtsps://)
    - Shell injection risks in parameters
    - GPU parameter compatibility
    
    Args:
        url: RTSP URL to validate
        params: FFmpeg parameters
        gpu_backend: Detected GPU (nvidia/amd/intel/none)
        
    Returns:
        True if valid and safe
    """
    # Validate URL
    if not url or not isinstance(url, str):
        logger.warning("Invalid URL: empty or wrong type")
        return False
    
    url_lower = url.lower()
    if not url_lower.startswith(("rtsp://", "rtsps://")):
        logger.warning(f"Invalid scheme: {url[:20]}")
        return False
    
    # Parse URL structure
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            logger.warning("URL missing host")
            return False
    except Exception as e:
        logger.warning(f"URL parse failed: {e}")
        return False
    
    # Validate params
    for param in params:
        if not isinstance(param, str):
            logger.warning(f"Invalid param type: {type(param)}")
            return False
        
        # Check shell injection risks
        if any(char in param for char in FORBIDDEN_SHELL_CHARS):
            logger.warning(f"Forbidden char in param: {param}")
            return False
    
    # Warn if GPU params but no GPU
    if gpu_backend == "none":
        gpu_flags = {"-hwaccel", "-hwaccel_output_format", "-c:v"}
        if any(any(flag in param for flag in gpu_flags) for param in params):
            logger.warning("GPU params used but no GPU detected")
            return False
    
    return True


logger.debug("RTSP utilities module loaded")
