"""RTSP utilities for playback and frame generation."""
import logging
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


async def generate_mjpeg_stream(
    rtsp_url: str, 
    max_fps: float = 5.0,
    stream_id: Optional[str] = None
) -> AsyncGenerator[bytes, None]:
    """Generate MJPEG frames from RTSP stream at specified FPS cap.
    
    Args:
        rtsp_url: RTSP URL to decode
        max_fps: Maximum frames per second (default 5.0)
        stream_id: Optional stream ID for status persistence on failure
        
    Yields:
        JPEG frame bytes with multipart boundary
        
    Raises:
        RuntimeError: If stream cannot be opened or fails during playback
    """
    import cv2
    import asyncio
    import time
    from concurrent.futures import ThreadPoolExecutor
    
    cap = None
    frame_interval = 1.0 / max_fps  # Time between frames in seconds
    
    async def _mark_stream_inactive():
        """Mark stream as inactive in config on failure."""
        if stream_id:
            try:
                from ..config_io import load_streams, save_streams
                streams = load_streams()
                for stream in streams:
                    if stream.get("id") == stream_id and stream.get("status") != "Inactive":
                        stream["status"] = "Inactive"
                        save_streams(streams)
                        logger.warning(f"Marked stream {stream_id} as Inactive due to playback failure")
                        break
            except Exception as e:
                logger.error(f"Failed to mark stream {stream_id} as Inactive: {e}")
    
    try:
        # Open RTSP stream
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open RTSP stream: {rtsp_url}")
        
        logger.info(f"Started MJPEG stream for {rtsp_url} at max {max_fps} FPS")
        
        last_frame_time = 0.0
        
        while True:
            current_time = time.time()
            
            # Throttle to max FPS
            time_since_last_frame = current_time - last_frame_time
            if time_since_last_frame < frame_interval:
                await asyncio.sleep(frame_interval - time_since_last_frame)
                current_time = time.time()
            
            # Read frame in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                ret, frame = await loop.run_in_executor(executor, cap.read)
            
            if not ret or frame is None:
                logger.warning(f"Failed to read frame from {rtsp_url}")
                raise RuntimeError("Stream ended or failed to read frame")
            
            # Encode frame as JPEG
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                logger.warning(f"Failed to encode frame as JPEG for {rtsp_url}")
                continue
            
            # Yield frame with multipart boundary
            frame_bytes = jpeg.tobytes()
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
            )
            
            last_frame_time = current_time
            
    except Exception as e:
        logger.error(f"MJPEG stream error for {rtsp_url}: {e}")
        # Mark stream as inactive on failure
        await _mark_stream_inactive()
        raise RuntimeError(f"Stream playback failed: {e}")
    finally:
        if cap is not None:
            cap.release()
            logger.info(f"Released RTSP stream: {rtsp_url}")


async def probe_rtsp_stream(rtsp_url: str, timeout_seconds: float = 2.0) -> bool:
    """Probe RTSP stream to check connectivity.
    
    Attempts to read a single frame to verify the stream is reachable.
    
    Args:
        rtsp_url: RTSP URL to probe
        timeout_seconds: Timeout for probe attempt (default 2.0)
        
    Returns:
        True if stream is reachable, False otherwise
    """
    import cv2
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    def _probe_sync():
        """Synchronous probe function to run in thread pool."""
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
        # Run blocking OpenCV call in thread pool with timeout
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await asyncio.wait_for(
                loop.run_in_executor(executor, _probe_sync),
                timeout=timeout_seconds
            )
            return result
    except asyncio.TimeoutError:
        logger.debug(f"RTSP probe timeout for {rtsp_url}")
        return False
    except Exception as e:
        logger.debug(f"RTSP probe error for {rtsp_url}: {e}")
        return False


def probe_rtsp_stream(rtsp_url: str, timeout_seconds: float = 2.0) -> bool:
    """Probe RTSP stream reachability using ffprobe.
    
    Args:
        rtsp_url: RTSP URL to probe
        timeout_seconds: Probe timeout
        
    Returns:
        True if stream is reachable
    """
    from subprocess import run, PIPE, timeout
    cmd = [
        "ffprobe",
        "-hide_banner",
        "-loglevel", "error",
        "-timeout", str(int(timeout_seconds * 1e6)),  # microseconds
        "-i", rtsp_url
    ]
    try:
        result = run(cmd, stdout=PIPE, stderr=PIPE, timeout=timeout_seconds)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
