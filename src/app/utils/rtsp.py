"""RTSP stream utilities for frame generation and validation."""
from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator, Final
from dataclasses import dataclass

import cv2

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

DEFAULT_FPS: Final[float] = 5.0
DEFAULT_JPEG_QUALITY: Final[int] = 85
DEFAULT_PROBE_TIMEOUT: Final[float] = 2.0
MAX_THREAD_WORKERS: Final[int] = 1

# Shell metacharacters that should not appear in FFmpeg params
FORBIDDEN_SHELL_CHARS: Final[set[str]] = {";", "&", "|", ">", "<", "`", "$", "\n", "\r"}

# GPU-specific FFmpeg flags
GPU_FFMPEG_FLAGS: Final[set[str]] = {"-hwaccel", "-hwaccel_output_format", "-c:v"}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FFmpegConfig:
    """FFmpeg configuration for stream processing."""
    rtsp_url: str
    custom_params: list[str]
    target_fps: int
    gpu_backend: str | None = None
    jpeg_quality: int = 8  # 1-31, lower is better


# ============================================================================
# MJPEG Stream Generation
# ============================================================================

async def generate_mjpeg_stream(
    rtsp_url: str,
    max_fps: float = DEFAULT_FPS,
    stream_id: str | None = None,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY
) -> AsyncGenerator[bytes, None]:
    """Generate MJPEG frames from RTSP stream with FPS throttling.
    
    Opens an RTSP stream, reads frames at the specified FPS rate, encodes
    them as JPEG, and yields them with multipart/x-mixed-replace boundaries.
    
    Args:
        rtsp_url: RTSP URL to decode
        max_fps: Maximum frames per second (default: 5.0)
        stream_id: Optional stream ID for error handling
        jpeg_quality: JPEG encoding quality 0-100 (default: 85)
        
    Yields:
        JPEG frame bytes with multipart boundary headers
        
    Raises:
        RuntimeError: If stream cannot be opened or fails during playback
        
    Example:
        ```
        async for frame in generate_mjpeg_stream("rtsp://cam/stream"):
            # Send frame to client
            yield frame
        ```
    """
    cap = None
    frame_interval = 1.0 / max_fps
    last_frame_time = 0.0
    
    try:
        # Open RTSP stream in thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=MAX_THREAD_WORKERS) as executor:
            cap = await loop.run_in_executor(
                executor,
                lambda: cv2.VideoCapture(rtsp_url)
            )
        
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open RTSP stream: {rtsp_url}")
        
        logger.info(f"Started MJPEG stream for {rtsp_url} at {max_fps} FPS")
        
        while True:
            current_time = time.time()
            
            # Throttle to max FPS
            time_since_last = current_time - last_frame_time
            if time_since_last < frame_interval:
                await asyncio.sleep(frame_interval - time_since_last)
                current_time = time.time()
            
            # Read frame in thread pool to avoid blocking event loop
            with ThreadPoolExecutor(max_workers=MAX_THREAD_WORKERS) as executor:
                ret, frame = await loop.run_in_executor(executor, cap.read)
            
            if not ret or frame is None:
                logger.warning(f"Failed to read frame from {rtsp_url}")
                await _mark_stream_inactive(stream_id)
                raise RuntimeError("Stream ended or failed to read frame")
            
            # Encode frame as JPEG
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
            ret_encode, jpeg = cv2.imencode('.jpg', frame, encode_params)
            
            if not ret_encode:
                logger.warning(f"Failed to encode frame as JPEG for {rtsp_url}")
                continue
            
            # Yield frame with multipart boundary
            frame_bytes = jpeg.tobytes()
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n'
                b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' +
                frame_bytes + b'\r\n'
            )
            
            last_frame_time = current_time
            
    except asyncio.CancelledError:
        logger.info(f"MJPEG stream cancelled for {rtsp_url}")
        raise
        
    except Exception as e:
        logger.error(f"MJPEG stream error for {rtsp_url}: {e}", exc_info=True)
        await _mark_stream_inactive(stream_id)
        raise RuntimeError(f"Stream playback failed: {e}")
        
    finally:
        if cap is not None:
            cap.release()
            logger.info(f"Released RTSP stream: {rtsp_url}")


async def _mark_stream_inactive(stream_id: str | None) -> None:
    """Mark stream as inactive in configuration on failure."""
    if not stream_id:
        return
    
    try:
        from ..config_io import load_streams, save_streams
        
        config = load_streams()
        streams = config.get("streams", [])
        
        for stream in streams:
            if stream.get("id") == stream_id and stream.get("status") != "stopped":
                stream["status"] = "stopped"
                config["streams"] = streams
                save_streams(config)
                logger.warning(f"Marked stream {stream_id} as stopped due to failure")
                break
                
    except Exception as e:
        logger.error(f"Failed to mark stream {stream_id} as stopped: {e}")



# ============================================================================
# RTSP Stream Probing
# ============================================================================

async def probe_rtsp_stream(
    rtsp_url: str,
    timeout_seconds: float = DEFAULT_PROBE_TIMEOUT
) -> bool:
    """Probe RTSP stream to verify connectivity and readability.
    
    Attempts to open the stream and read a single frame to verify it's
    accessible and properly formatted.
    
    Args:
        rtsp_url: RTSP URL to probe
        timeout_seconds: Timeout for probe attempt (default: 2.0 seconds)
        
    Returns:
        True if stream is reachable and readable, False otherwise
        
    Example:
        ```
        if await probe_rtsp_stream("rtsp://cam/stream"):
            print("Stream is accessible")
        ```
    """
    def _probe_sync() -> bool:
        """Synchronous probe function for thread pool execution."""
        cap = None
        try:
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                return False
            
            # Try to read a single frame
            ret, frame = cap.read()
            return ret and frame is not None
            
        except Exception as e:
            logger.debug(f"RTSP probe failed for {rtsp_url}: {e}")
            return False
            
        finally:
            if cap is not None:
                cap.release()
    
    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=MAX_THREAD_WORKERS) as executor:
            result = await asyncio.wait_for(
                loop.run_in_executor(executor, _probe_sync),
                timeout=timeout_seconds
            )
            return result
            
    except asyncio.TimeoutError:
        logger.debug(f"RTSP probe timeout for {rtsp_url} after {timeout_seconds}s")
        return False
        
    except Exception as e:
        logger.debug(f"RTSP probe error for {rtsp_url}: {e}")
        return False


# ============================================================================
# FFmpeg Command Building
# ============================================================================

def build_ffmpeg_command(
    rtsp_url: str,
    ffmpeg_params: list[str],
    target_fps: int,
    gpu_backend: str | None = None
) -> list[str]:
    """Build FFmpeg command with optional GPU acceleration.
    
    Constructs FFmpeg command line arguments for RTSP stream processing,
    including user-provided parameters and GPU acceleration flags.
    
    Args:
        rtsp_url: RTSP URL to process
        ffmpeg_params: User-provided FFmpeg parameters
        target_fps: Target frames per second
        gpu_backend: GPU backend (nvidia, amd, intel, or None for CPU)
        
    Returns:
        List of command arguments for subprocess execution
        
    Example:
        ```
        cmd = build_ffmpeg_command(
            "rtsp://cam/stream",
            ["-rtsp_transport", "tcp"],
            30,
            "nvidia"
        )
        subprocess.run(cmd)
        ```
    """
    cmd = ["ffmpeg"]
    
    # Add GPU acceleration flags if enabled
    if gpu_backend and gpu_backend != "none":
        if gpu_backend == "nvidia":
            cmd.extend(["-hwaccel", "cuda"])
        elif gpu_backend == "amd":
            cmd.extend(["-hwaccel", "vaapi"])
        elif gpu_backend == "intel":
            cmd.extend(["-hwaccel", "qsv"])
    
    # Add user-provided parameters
    cmd.extend(ffmpeg_params)
    
    # Add input
    cmd.extend(["-i", rtsp_url])
    
    # Add FPS filter
    cmd.extend(["-r", str(target_fps)])
    
    # Add output format (MJPEG to stdout)
    cmd.extend([
        "-c:v", "mjpeg",
        "-q:v", "8",  # Quality (1-31, lower is better)
        "-f", "mjpeg",
        "-"  # Output to stdout
    ])
    
    return cmd


# ============================================================================
# Validation
# ============================================================================

def validate_rtsp_url(url: str, params: list[str], gpu_backend: str) -> bool:
    """Validate RTSP URL and FFmpeg parameters for security and compatibility.
    
    Checks:
    - URL format and protocol
    - Shell injection risks in parameters
    - GPU parameter compatibility with detected hardware
    
    Args:
        url: RTSP URL to validate
        params: FFmpeg parameters to validate
        gpu_backend: Detected GPU backend (nvidia, amd, intel, none)
        
    Returns:
        True if valid and safe, False otherwise
        
    Example:
        ```
        if validate_rtsp_url(url, params, "nvidia"):
            # Safe to proceed
            cmd = build_ffmpeg_command(...)
        ```
    """
    # Validate URL format
    if not url or not isinstance(url, str):
        logger.warning("RTSP URL is empty or invalid type")
        return False
    
    url_lower = url.lower()
    if not url_lower.startswith("rtsp://") and not url_lower.startswith("rtsps://"):
        logger.warning(f"Invalid RTSP URL scheme: {url}")
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


def validate_ffmpeg_config(config: FFmpegConfig) -> tuple[bool, str | None]:
    """Validate complete FFmpeg configuration.
    
    Args:
        config: FFmpeg configuration to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate URL
    if not validate_rtsp_url(config.rtsp_url, config.custom_params, config.gpu_backend or "none"):
        return False, "Invalid RTSP URL or parameters"
    
    # Validate FPS
    if not (0.1 <= config.target_fps <= 120):
        return False, f"Target FPS must be between 0.1 and 120 (got {config.target_fps})"
    
    # Validate JPEG quality
    if not (1 <= config.jpeg_quality <= 31):
        return False, f"JPEG quality must be between 1 and 31 (got {config.jpeg_quality})"
    
    return True, None
