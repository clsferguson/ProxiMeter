"""Stream management service with business logic."""
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime
import uuid
import subprocess
import os
import asyncio
import cv2

from ..config_io import load_streams, save_streams
from ..models.stream import Stream, NewStream
from ..utils.validation import validate_rtsp_url as validate_rtsp_url_format
from ..utils.strings import normalize_stream_name
from ..utils.rtsp import probe_rtsp_stream, build_ffmpeg_command, validate_rtsp_url

logger = logging.getLogger(__name__)

class StreamsService:
    """Service for managing streams with validation and persistence."""
    
    def __init__(self, config_path: str = "/app/config/config.yml"):
        """Initialize the streams service.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = config_path
        self.active_processes: Dict[str, Dict[str, Any]] = {}
        self.gpu_backend = os.environ.get("GPU_BACKEND_DETECTED", "none")
        logger.info(f"StreamsService initialized with config: {config_path}")
    
    async def list_streams(self) -> List[dict]:
        """List all streams.
        
        Returns:
            List of stream dictionaries sorted by order
        """
        streams = load_streams()
        # Sort by order field
        streams.sort(key=lambda s: s.get("order", 0))
        return streams
    
    async def create_stream(
        self,
        name: str,
        rtsp_url: str,
        hw_accel_enabled: bool = True,
        ffmpeg_params: Optional[List[str]] = None,
        target_fps: int = 5
    ) -> dict:
        """Create a new stream with validation.
        
        Args:
            name: Stream name (1-50 chars, unique CI)
            rtsp_url: RTSP URL starting with rtsp://
            hw_accel_enabled: Hardware acceleration flag
            ffmpeg_params: FFmpeg parameters
            target_fps: Target frames per second
            
        Returns:
            Created stream dictionary
            
        Raises:
            ValueError: If validation fails
        """
        # Validate and normalize inputs
        name = name.strip()
        rtsp_url = rtsp_url.strip()
        
        if not name or len(name) > 50:
            raise ValueError("Name must be 1-50 characters after trimming")
        
        # Validate RTSP URL format
        is_valid, error_msg = validate_rtsp_url_format(rtsp_url)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Load existing streams
        streams = load_streams()
        
        # Check for duplicate name (case-insensitive)
        normalized_name = normalize_stream_name(name)
        for stream in streams:
            if normalize_stream_name(stream.get("name", "")) == normalized_name:
                raise ValueError(f"Stream name '{name}' already exists (case-insensitive)")
        
        # Probe RTSP stream (2s timeout)
        logger.info(f"Probing RTSP stream: {rtsp_url}")
        is_reachable = await probe_rtsp_stream(rtsp_url, timeout_seconds=2.0)
        if not is_reachable:
            logger.warning(f"RTSP URL not reachable: {rtsp_url}")
        
        # Create stream object
        stream = Stream(
            id=str(uuid.uuid4()),
            name=name,
            rtsp_url=rtsp_url,
            hw_accel_enabled=hw_accel_enabled,
            ffmpeg_params=ffmpeg_params or self.default_ffmpeg_params(),
            target_fps=target_fps,
            created_at=datetime.utcnow().isoformat() + "Z",
            order=len(streams),
            status="stopped"  # Initial status
        )
        
        # Add to streams list and save
        streams.append(stream.model_dump())
        save_streams(streams)
        
        logger.info(f"Created stream {stream.id} with status {stream.status}")
        return stream.model_dump()
    
    async def get_stream(self, stream_id: str) -> Optional[dict]:
        """Get a stream by ID.
        
        Args:
            stream_id: Stream UUID
            
        Returns:
            Stream dictionary or None if not found
        """
        streams = load_streams()
        for stream in streams:
            if stream.get("id") == stream_id:
                return stream
        return None
    
    async def update_stream(
        self,
        stream_id: str,
        name: Optional[str] = None,
        rtsp_url: Optional[str] = None,
        status: Optional[str] = None,
        hw_accel_enabled: Optional[bool] = None,
        ffmpeg_params: Optional[List[str]] = None,
        target_fps: Optional[int] = None
    ) -> Optional[dict]:
        """Update a stream (partial update).
        
        Args:
            stream_id: Stream UUID
            name: New name (optional)
            rtsp_url: New RTSP URL (optional)
            status: New status (optional)
            hw_accel_enabled: New hardware acceleration flag (optional)
            ffmpeg_params: New FFmpeg parameters (optional)
            target_fps: New target FPS (optional)
            
        Returns:
            Updated stream dictionary or None if not found
            
        Raises:
            ValueError: If validation fails
        """
        # Load existing streams
        streams = load_streams()
        
        # Find the stream to update
        stream_index = None
        for i, stream in enumerate(streams):
            if stream.get("id") == stream_id:
                stream_index = i
                break
        
        if stream_index is None:
            return None
        
        stream = streams[stream_index]
        url_changed = False
        
        # Update name if provided
        if name is not None:
            name = name.strip()
            if not name or len(name) > 50:
                raise ValueError("Name must be 1-50 characters after trimming")
            
            # Check for duplicate name (case-insensitive), excluding current stream
            normalized_name = normalize_stream_name(name)
            for i, s in enumerate(streams):
                if i != stream_index and normalize_stream_name(s.get("name", "")) == normalized_name:
                    raise ValueError(f"Stream name '{name}' already exists (case-insensitive)")
            
            stream["name"] = name
        
        # Update RTSP URL if provided
        if rtsp_url is not None:
            rtsp_url = rtsp_url.strip()
            
            # Validate RTSP URL format
            is_valid, error_msg = validate_rtsp_url_format(rtsp_url)
            if not is_valid:
                raise ValueError(error_msg)
            
            stream["rtsp_url"] = rtsp_url
            url_changed = True
        
        # Update hardware acceleration if provided
        if hw_accel_enabled is not None:
            stream["hw_accel_enabled"] = hw_accel_enabled
        
        # Update FFmpeg params if provided
        if ffmpeg_params is not None:
            stream["ffmpeg_params"] = ffmpeg_params
        
        # Update target FPS if provided
        if target_fps is not None:
            if not (1 <= target_fps <= 30):
                raise ValueError("Target FPS must be between 1 and 30")
            stream["target_fps"] = target_fps
        
        # Re-probe if URL changed
        if url_changed:
            logger.info(f"Re-probing RTSP stream {stream_id} after URL change")
            is_reachable = await probe_rtsp_stream(stream["rtsp_url"], timeout_seconds=2.0)
            # Note: Don't auto-update status here, let the caller control it
            if not is_reachable:
                logger.warning(f"Updated RTSP URL not reachable for stream {stream_id}")
        
        # Update status if provided
        if status is not None:
            stream["status"] = status
        
        # Save updated streams
        streams[stream_index] = stream
        save_streams(streams)
        
        logger.info(f"Updated stream {stream_id}")
        return stream
    
    async def delete_stream(self, stream_id: str) -> bool:
        """Delete a stream and renumber orders.
        
        Args:
            stream_id: Stream UUID
            
        Returns:
            True if deleted, False if not found
        """
        # Stop stream if running
        if stream_id in self.active_processes:
            await self.stop_stream(stream_id)
        
        # Load existing streams
        streams = load_streams()
        
        # Find and remove the stream
        stream_found = False
        for i, stream in enumerate(streams):
            if stream.get("id") == stream_id:
                streams.pop(i)
                stream_found = True
                logger.info(f"Deleted stream {stream_id}")
                break
        
        if not stream_found:
            return False
        
        # Renumber remaining streams (contiguous ordering starting at 0)
        for i, stream in enumerate(streams):
            stream["order"] = i
        
        # Save updated streams
        save_streams(streams)
        
        logger.info(f"Renumbered {len(streams)} remaining streams")
        return True
    
    async def reorder_streams(self, order: List[str]) -> bool:
        """Reorder streams by ID list.
        
        Args:
            order: List of stream UUIDs in desired order
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If order is invalid (duplicates, missing IDs)
        """
        # Load existing streams
        streams = load_streams()
        
        # No-op if 0 or 1 streams
        if len(streams) <= 1:
            logger.info("Reorder no-op: ≤1 streams")
            return True
        
        # Validate order list
        if len(order) != len(streams):
            raise ValueError(f"Order list must contain exactly {len(streams)} stream IDs")
        
        # Check for duplicates
        if len(set(order)) != len(order):
            raise ValueError("Order list contains duplicate IDs")
        
        # Build a map of existing streams by ID
        stream_map = {s.get("id"): s for s in streams}
        
        # Validate all IDs exist
        for stream_id in order:
            if stream_id not in stream_map:
                raise ValueError(f"Unknown stream ID in order list: {stream_id}")
        
        # Check if order is already the same (idempotent)
        current_order = [s.get("id") for s in streams]
        if current_order == order:
            logger.info("Reorder no-op: order unchanged")
            return True
        
        # Reorder streams according to the provided list
        reordered_streams = []
        for i, stream_id in enumerate(order):
            stream = stream_map[stream_id].copy()
            stream["order"] = i
            reordered_streams.append(stream)
        
        # Save reordered streams
        save_streams(reordered_streams)
        
        logger.info(f"Reordered {len(reordered_streams)} streams")
        return True
    
    async def start_stream(self, stream_id: str, stream: dict) -> bool:
        """Start FFmpeg processing for a stream.
        
        Args:
            stream_id: Stream ID
            stream: Stream dict with config
            
        Returns:
            True if started successfully
        """
        if stream_id in self.active_processes:
            logger.warning(f"Stream {stream_id} already running")
            return False
        
        if stream.get("hw_accel_enabled", True) and self.gpu_backend == "none":
            logger.error(f"Hardware acceleration requested but no GPU detected for stream {stream_id}")
            raise ValueError("GPU unavailable for hardware acceleration")
        
        # Validate URL and params
        url = stream["rtsp_url"]
        params = stream.get("ffmpeg_params", [])
        fps = stream.get("target_fps", 5)
        
        is_valid = validate_rtsp_url(url, params, self.gpu_backend)
        if not is_valid:
            raise ValueError("Invalid RTSP URL or FFmpeg params")
        
        # Build command
        cmd = build_ffmpeg_command(
            rtsp_url=url,
            ffmpeg_params=params,
            target_fps=fps,
            gpu_backend=self.gpu_backend if stream.get("hw_accel_enabled") else None
        )
        
        logger.info(f"Starting FFmpeg for stream {stream_id}: {' '.join(cmd)}")
        
        read_fd = None
        try:
            # Create a pipe using os.pipe() for file descriptor access
            read_fd, write_fd = os.pipe()
            
            # Start subprocess with write end of pipe as stdout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=write_fd,
                stderr=subprocess.PIPE
            )
            
            # Close write end in parent process (subprocess has it)
            os.close(write_fd)
            
            # Log stderr in background
            async def log_stderr():
                if process.stderr is None:
                    return
                async for line in process.stderr:
                    from ..logging_config import log_ffmpeg_stderr
                    log_ffmpeg_stderr(stream_id, line)
            
            asyncio.create_task(log_stderr())
            
            # Create VideoCapture with read file descriptor in thread pool
            loop = asyncio.get_event_loop()
            
            def open_capture():
                """Open VideoCapture with file descriptor in synchronous context."""
                try:
                    cap = cv2.VideoCapture()
                    # Use the read file descriptor
                    success = cap.open(read_fd, cv2.CAP_FFMPEG)
                    if not success:
                        logger.error(f"Failed to open VideoCapture for stream {stream_id}")
                        return None
                    return cap
                except Exception as e:
                    logger.error(f"Error opening VideoCapture: {e}")
                    return None
            
            # Run the blocking OpenCV operation in thread pool
            cap = await loop.run_in_executor(None, open_capture)
            
            if cap is None:
                if read_fd is not None:
                    os.close(read_fd)
                process.terminate()
                await process.wait()
                raise RuntimeError("Failed to open FFmpeg pipe with OpenCV")
            
            # Store process, cap, and read_fd for cleanup
            self.active_processes[stream_id] = {
                "process": process,
                "cap": cap,
                "read_fd": read_fd
            }
            
            # Update status
            stream["status"] = "running"
            streams = load_streams()
            for s in streams:
                if s["id"] == stream_id:
                    s["status"] = "running"
                    break
            save_streams(streams)
            
            logger.info(f"Started stream {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start stream {stream_id}: {e}", exc_info=True)
            # Clean up file descriptors if they exist
            if read_fd is not None:
                try:
                    os.close(read_fd)
                except OSError:
                    pass
            return False
    
    async def stop_stream(self, stream_id: str) -> bool:
        """Stop FFmpeg processing for a stream.
        
        Args:
            stream_id: Stream ID
            
        Returns:
            True if stopped successfully
        """
        if stream_id not in self.active_processes:
            logger.warning(f"Stream {stream_id} not running")
            return False
        
        proc_data = self.active_processes.pop(stream_id)
        process = proc_data["process"]
        cap = proc_data.get("cap")
        read_fd = proc_data.get("read_fd")
        
        # Release OpenCV capture
        if cap:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, cap.release)
        
        # Close file descriptor
        if read_fd is not None:
            try:
                os.close(read_fd)
            except OSError:
                pass
        
        # Terminate process
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(f"Stream {stream_id} did not terminate, killing...")
            process.kill()
            await process.wait()
        
        # Update status
        streams = load_streams()
        for s in streams:
            if s["id"] == stream_id:
                s["status"] = "stopped"
                break
        save_streams(streams)
        
        logger.info(f"Stopped stream {stream_id}")
        return True
    
    async def get_frame(self, stream_id: str) -> Optional[Tuple[bool, Any]]:
        """Get next frame from stream pipe.
        
        Args:
            stream_id: Stream ID
            
        Returns:
            Tuple of (success, frame) or None if stream not running
        """
        if stream_id not in self.active_processes:
            return None
        
        cap = self.active_processes[stream_id]["cap"]
        
        # Run blocking cv2.read() in thread pool
        loop = asyncio.get_event_loop()
        ret, frame = await loop.run_in_executor(None, cap.read)
        
        return (ret, frame)
    
    def default_ffmpeg_params(self) -> List[str]:
        """Get default FFmpeg params with GPU flags if available.
        
        Returns:
            List of default FFmpeg parameters
        """
        params = [
            "-hide_banner",
            "-loglevel", "warning",
            "-threads", "2",
            "-rtsp_transport", "tcp",
            "-timeout", "10000000"
        ]
        
        # Add GPU-specific flags if available
        if self.gpu_backend == "nvidia":
            params.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda", "-c:v", "h264_cuvid"])
        elif self.gpu_backend == "amd":
            params.extend(["-hwaccel", "amf", "-c:v", "h264_amf"])
        elif self.gpu_backend == "intel":
            params.extend(["-hwaccel", "qsv", "-c:v", "h264_qsv"])
        
        return params
