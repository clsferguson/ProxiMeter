"""Stream management service with FFmpeg process control.

This service manages the lifecycle of RTSP stream processing:
- Creating and persisting stream configurations
- Starting/stopping FFmpeg processes for stream decoding
- Managing OpenCV VideoCapture instances for frame access
- Auto-starting streams on application startup
- Coordinating hardware acceleration (CUDA/NVDEC)

Key features:
- Automatic stream startup for configured streams
- Process health monitoring and cleanup
- Thread-safe frame access
- Graceful shutdown handling

Updated: Added auto_start support for streams to automatically begin
processing when configured or when the application restarts.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, Final

import cv2

from ..config_io import load_streams, save_streams, get_gpu_backend
from ..models.stream import Stream
from ..utils.validation import validate_rtsp_url as validate_rtsp_url_format, validate_fps
from ..utils.strings import normalize_stream_name, mask_rtsp_credentials
from ..utils.rtsp import probe_rtsp_stream, build_ffmpeg_command, validate_rtsp_url

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_PROBE_TIMEOUT: Final[float] = 5.0
"""Timeout in seconds for probing RTSP stream connectivity."""

STREAM_STOP_TIMEOUT: Final[float] = 5.0
"""Timeout in seconds for gracefully stopping FFmpeg process."""

MIN_FPS: Final[int] = 1
"""Minimum allowed target FPS for stream processing."""

MAX_FPS: Final[int] = 30
"""Maximum allowed target FPS for stream processing."""


# ============================================================================
# Streams Service
# ============================================================================

class StreamsService:
    """Service for managing RTSP streams with FFmpeg processing.
    
    This service handles the complete lifecycle of stream processing:
    1. Configuration persistence (JSON file storage)
    2. FFmpeg subprocess management
    3. OpenCV VideoCapture coordination
    4. Frame access for MJPEG and detection
    5. Auto-start on creation and application startup
    
    Attributes:
        active_processes: Dict mapping stream_id to process info
        gpu_backend: Detected GPU backend (cuda, none, etc.)
    """
    
    def __init__(self) -> None:
        """Initialize streams service and detect GPU backend."""
        self.active_processes: dict[str, dict[str, Any]] = {}
        self.gpu_backend = get_gpu_backend()
        logger.info(f"StreamsService initialized with GPU backend: {self.gpu_backend}")
    
    # ========================================================================
    # Stream Retrieval
    # ========================================================================
    
    async def list_streams(self) -> list[dict]:
        """List all configured streams sorted by display order.
        
        Returns:
            List of stream dicts ordered by 'order' field
        """
        try:
            config = load_streams()
            streams = config.get("streams", [])
            streams.sort(key=lambda s: s.get("order", 0))
            logger.debug(f"Listed {len(streams)} streams")
            return streams
        except Exception as e:
            logger.error(f"Error listing streams: {e}", exc_info=True)
            return []
    
    async def get_stream(self, stream_id: str) -> dict | None:
        """Get a stream by ID.
        
        Args:
            stream_id: UUID of stream to retrieve
            
        Returns:
            Stream dict if found, None otherwise
        """
        try:
            config = load_streams()
            streams = config.get("streams", [])
            for stream in streams:
                if stream.get("id") == stream_id:
                    return stream
            logger.debug(f"Stream {stream_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting stream {stream_id}: {e}", exc_info=True)
            return None
    
    # ========================================================================
    # Stream Creation
    # ========================================================================
    
    async def create_stream(
        self,
        name: str,
        rtsp_url: str,
        hw_accel_enabled: bool = True,
        ffmpeg_params: list[str] | None = None,
        target_fps: int = 5,
        auto_start: bool = True
    ) -> dict:
        """Create a new stream with validation and optional auto-start.
        
        Creates stream configuration, validates RTSP connectivity, persists
        to storage, and optionally starts FFmpeg processing immediately.
        
        Args:
            name: Display name for stream (1-50 characters)
            rtsp_url: RTSP URL to stream source
            hw_accel_enabled: Whether to use GPU hardware acceleration
            ffmpeg_params: Optional additional FFmpeg parameters
            target_fps: Target frame rate for processing (1-30)
            auto_start: Whether to automatically start stream on creation
            
        Returns:
            Created stream dict with all fields
            
        Raises:
            ValueError: If validation fails (invalid name, URL, FPS, etc.)
        """
        # Normalize inputs
        name = name.strip()
        rtsp_url = rtsp_url.strip()
        
        # Validate name
        if not name or len(name) > 50:
            raise ValueError("Stream name must be 1-50 characters")
        
        # Validate RTSP URL format
        is_valid, error_msg = validate_rtsp_url_format(rtsp_url)
        if not is_valid:
            raise ValueError(error_msg or "Invalid RTSP URL")
        
        # Validate FPS
        is_valid, error_msg = validate_fps(target_fps, MIN_FPS, MAX_FPS)
        if not is_valid:
            raise ValueError(error_msg or "Invalid FPS")
        
        # Load existing config
        config = load_streams()
        streams = config.get("streams", [])
        
        # Check for duplicate name (case-insensitive)
        self._validate_unique_stream_name(streams, name)
        
        # Probe RTSP stream connectivity
        logger.info(f"Probing RTSP stream: {mask_rtsp_credentials(rtsp_url)}")
        is_reachable = await probe_rtsp_stream(rtsp_url, DEFAULT_PROBE_TIMEOUT)
        if not is_reachable:
            logger.warning(f"RTSP URL not reachable: {mask_rtsp_credentials(rtsp_url)}")
        
        # Determine initial status
        initial_status = "stopped"
        
        # Create stream object
        stream = Stream(
            id=str(uuid.uuid4()),
            name=name,
            rtsp_url=rtsp_url,
            hw_accel_enabled=hw_accel_enabled,
            ffmpeg_params=ffmpeg_params if ffmpeg_params is not None else [],
            target_fps=target_fps,
            auto_start=auto_start,
            created_at=datetime.now(timezone.utc).isoformat(),
            order=len(streams),
            status=initial_status
        )
        
        # Persist
        stream_dict = stream.model_dump()
        streams.append(stream_dict)
        config["streams"] = streams
        save_streams(config)
        
        logger.info(f"Created stream {stream.id}: {name} (auto_start={auto_start})")
        
        # Auto-start if enabled
        if auto_start:
            logger.info(f"Auto-starting stream {stream.id}")
            asyncio.create_task(self.start_stream(stream.id, stream_dict))
        
        return stream_dict
    
    # ========================================================================
    # Stream Updates
    # ========================================================================
    
    async def update_stream(
        self,
        stream_id: str,
        name: str | None = None,
        rtsp_url: str | None = None,
        status: str | None = None,
        hw_accel_enabled: bool | None = None,
        ffmpeg_params: list[str] | None = None,
        target_fps: int | None = None,
        auto_start: bool | None = None
    ) -> dict | None:
        """Update a stream (partial update).
        
        Updates only the fields provided. If RTSP URL changes, re-probes
        connectivity. If stream is running and critical params change,
        restart may be required (not automatic).
        
        Args:
            stream_id: UUID of stream to update
            name: New display name
            rtsp_url: New RTSP URL
            status: New status (running/stopped)
            hw_accel_enabled: Hardware acceleration toggle
            ffmpeg_params: New FFmpeg parameters
            target_fps: New target FPS
            auto_start: New auto-start setting
            
        Returns:
            Updated stream dict if found, None otherwise
            
        Raises:
            ValueError: If validation fails
        """
        config = load_streams()
        streams = config.get("streams", [])
        
        # Find stream
        stream_index = self._find_stream_index(streams, stream_id)
        if stream_index is None:
            logger.debug(f"Stream {stream_id} not found")
            return None
        
        stream = streams[stream_index]
        url_changed = False
        
        # Update name
        if name is not None:
            name = name.strip()
            if not name or len(name) > 50:
                raise ValueError("Stream name must be 1-50 characters")
            self._validate_unique_stream_name(streams, name, exclude_index=stream_index)
            stream["name"] = name
        
        # Update RTSP URL
        if rtsp_url is not None:
            rtsp_url = rtsp_url.strip()
            is_valid, error_msg = validate_rtsp_url_format(rtsp_url)
            if not is_valid:
                raise ValueError(error_msg or "Invalid RTSP URL")
            stream["rtsp_url"] = rtsp_url
            url_changed = True
        
        # Update hardware acceleration
        if hw_accel_enabled is not None:
            stream["hw_accel_enabled"] = hw_accel_enabled
        
        # Update FFmpeg params
        if ffmpeg_params is not None:
            stream["ffmpeg_params"] = ffmpeg_params
        
        # Update target FPS
        if target_fps is not None:
            is_valid, error_msg = validate_fps(target_fps, MIN_FPS, MAX_FPS)
            if not is_valid:
                raise ValueError(error_msg or "Invalid FPS")
            stream["target_fps"] = target_fps
        
        # Update auto-start
        if auto_start is not None:
            stream["auto_start"] = auto_start
        
        # Re-probe if URL changed
        if url_changed:
            logger.info(f"Re-probing stream {stream_id}")
            is_reachable = await probe_rtsp_stream(stream["rtsp_url"], DEFAULT_PROBE_TIMEOUT)
            if not is_reachable:
                logger.warning(f"Updated RTSP URL not reachable: {stream_id}")
        
        # Update status
        if status is not None:
            stream["status"] = status
        
        # Persist
        config["streams"] = streams
        save_streams(config)
        
        logger.info(f"Updated stream {stream_id}")
        return stream
    
    # ========================================================================
    # Stream Deletion
    # ========================================================================
    
    async def delete_stream(self, stream_id: str) -> bool:
        """Delete a stream and stop it if running.
        
        Stops FFmpeg process if active, removes configuration,
        and renumbers remaining streams.
        
        Args:
            stream_id: UUID of stream to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Stop stream if running
        if stream_id in self.active_processes:
            await self.stop_stream(stream_id)
        
        config = load_streams()
        streams = config.get("streams", [])
        
        # Find and remove
        initial_count = len(streams)
        streams = [s for s in streams if s.get("id") != stream_id]
        
        if len(streams) == initial_count:
            logger.debug(f"Stream {stream_id} not found")
            return False
        
        # Renumber orders
        for i, stream in enumerate(streams):
            stream["order"] = i
        
        config["streams"] = streams
        save_streams(config)
        
        logger.info(f"Deleted stream {stream_id}")
        return True
    
    # ========================================================================
    # Stream Reordering
    # ========================================================================
    
    async def reorder_streams(self, order: list[str]) -> bool:
        """Reorder streams by ID list.
        
        Args:
            order: List of stream IDs in desired display order
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If order list is invalid
        """
        config = load_streams()
        streams = config.get("streams", [])
        
        # No-op for 0 or 1 streams
        if len(streams) <= 1:
            logger.debug("Reorder no-op: ≤1 streams")
            return True
        
        # Validate
        if len(order) != len(streams):
            raise ValueError(f"Order must contain {len(streams)} IDs")
        
        if len(set(order)) != len(order):
            raise ValueError("Order contains duplicate IDs")
        
        # Build map
        stream_map = {s.get("id"): s for s in streams}
        
        # Validate all IDs exist
        for stream_id in order:
            if stream_id not in stream_map:
                raise ValueError(f"Unknown stream ID: {stream_id}")
        
        # Check if already correct (idempotent)
        current_order = [s.get("id") for s in streams]
        if current_order == order:
            logger.debug("Reorder no-op: unchanged")
            return True
        
        # Reorder
        reordered = []
        for i, stream_id in enumerate(order):
            stream = stream_map[stream_id].copy()
            stream["order"] = i
            reordered.append(stream)
        
        config["streams"] = reordered
        save_streams(config)
        logger.info(f"Reordered {len(reordered)} streams")
        return True
    
    # ========================================================================
    # Auto-Start Support
    # ========================================================================
    
    async def auto_start_configured_streams(self) -> None:
        """Auto-start all streams with auto_start=True.
        
        Called on application startup to resume previously running streams
        or start newly configured streams with auto-start enabled.
        
        Starts each stream as a background task to avoid blocking startup.
        """
        try:
            streams = await self.list_streams()
            auto_start_count = 0
            
            for stream in streams:
                if stream.get("auto_start", False):
                    stream_id = stream["id"]
                    stream_name = stream.get("name", "Unknown")
                    
                    logger.info(f"Auto-starting stream: {stream_name} ({stream_id})")
                    
                    # Start as background task
                    asyncio.create_task(self.start_stream(stream_id, stream))
                    auto_start_count += 1
            
            if auto_start_count > 0:
                logger.info(f"Queued {auto_start_count} streams for auto-start")
            else:
                logger.info("No streams configured for auto-start")
                
        except Exception as e:
            logger.error(f"Error during auto-start: {e}", exc_info=True)
    
    # ========================================================================
    # FFmpeg Process Control
    # ========================================================================
    
    async def start_stream(self, stream_id: str, stream: dict) -> bool:
        """Start FFmpeg processing for a stream.
        
        Starts FFmpeg subprocess to decode RTSP stream, creates pipe for
        frame data, and opens OpenCV VideoCapture to read frames.
        
        Args:
            stream_id: UUID of stream to start
            stream: Stream configuration dict
            
        Returns:
            True if started successfully, False otherwise
        """
        try:
            if stream_id in self.active_processes:
                logger.warning(f"Stream {stream_id} already running")
                return True
            
            # Validate GPU requirements
            if stream.get("hw_accel_enabled") and self.gpu_backend == "none":
                raise ValueError("Hardware acceleration unavailable (no GPU detected)")
            
            # Get parameters
            url = stream["rtsp_url"]
            params = stream.get("ffmpeg_params", [])
            fps = stream.get("target_fps", 5)
            hw_accel = stream.get("hw_accel_enabled", False)
            
            # Validate
            if not validate_rtsp_url(url, params, self.gpu_backend):
                raise ValueError("Invalid RTSP URL or FFmpeg params")
            
            # Build command
            cmd = build_ffmpeg_command(
                rtsp_url=url,
                ffmpeg_params=params,
                target_fps=fps,
                gpu_backend=self.gpu_backend if hw_accel else None
            )
            
            logger.info(f"Starting FFmpeg for {stream_id}: {mask_rtsp_credentials(url)}")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            
            # Create pipe
            read_fd, write_fd = os.pipe()
            
            # Start subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=write_fd,
                stderr=subprocess.PIPE
            )
            
            # Close write end in parent
            os.close(write_fd)
            
            # Wait a moment for process to initialize
            await asyncio.sleep(0.5)
            
            # Check if process died
            if process.returncode is not None:
                os.close(read_fd)
                stderr = await process.stderr.read() if process.stderr else b""
                error_msg = stderr.decode().strip()
                logger.error(f"FFmpeg died immediately for {stream_id}: {error_msg}")
                raise RuntimeError(f"FFmpeg failed to start: {error_msg}")
            
            # Open VideoCapture with file descriptor
            loop = asyncio.get_event_loop()
            
            def open_capture():
                try:
                    cap = cv2.VideoCapture(f"pipe:{read_fd}")
                    if not cap.isOpened():
                        return None
                    return cap
                except Exception as e:
                    logger.error(f"Error opening VideoCapture: {e}")
                    return None
            
            cap = await loop.run_in_executor(None, open_capture)
            
            if cap is None:
                os.close(read_fd)
                process.terminate()
                await process.wait()
                raise RuntimeError("Failed to open FFmpeg pipe with OpenCV")
            
            # Store process info
            self.active_processes[stream_id] = {
                "process": process,
                "cap": cap,
                "read_fd": read_fd
            }
            
            # Update status in config
            config = load_streams()
            streams = config.get("streams", [])
            for s in streams:
                if s.get("id") == stream_id:
                    s["status"] = "running"
                    break
            config["streams"] = streams
            save_streams(config)
            
            logger.info(f"Successfully started stream {stream_id} (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start stream {stream_id}: {e}", exc_info=True)
            
            # Cleanup on failure
            if stream_id in self.active_processes:
                proc_data = self.active_processes.pop(stream_id)
                if "read_fd" in proc_data:
                    try:
                        os.close(proc_data["read_fd"])
                    except OSError:
                        pass
            
            return False
    
    async def stop_stream(self, stream_id: str) -> bool:
        """Stop FFmpeg processing for a stream.
        
        Releases OpenCV capture, closes pipe, and terminates FFmpeg process.
        Uses graceful termination with fallback to kill after timeout.
        
        Args:
            stream_id: UUID of stream to stop
            
        Returns:
            True if stopped successfully, False if not running
        """
        if stream_id not in self.active_processes:
            logger.warning(f"Stream {stream_id} not running")
            return False
        
        try:
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
                await asyncio.wait_for(process.wait(), timeout=STREAM_STOP_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning(f"Stream {stream_id} timeout, killing")
                process.kill()
                await process.wait()
            
            # Update status
            config = load_streams()
            streams = config.get("streams", [])
            for s in streams:
                if s.get("id") == stream_id:
                    s["status"] = "stopped"
                    break
            config["streams"] = streams
            save_streams(config)
            
            logger.info(f"Stopped stream {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping stream {stream_id}: {e}", exc_info=True)
            return False
    
    async def get_frame(self, stream_id: str) -> tuple[bool, Any] | None:
        """Get next frame from stream pipe.
        
        Reads one frame from OpenCV VideoCapture. This is a blocking
        operation executed in thread pool.
        
        Args:
            stream_id: UUID of stream to read from
            
        Returns:
            Tuple of (success, frame) if stream active, None otherwise
        """
        if stream_id not in self.active_processes:
            return None
        
        cap = self.active_processes[stream_id]["cap"]
        
        # Run blocking cv2.read() in thread pool
        loop = asyncio.get_event_loop()
        ret, frame = await loop.run_in_executor(None, cap.read)
        
        return (ret, frame)
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _find_stream_index(self, streams: list[dict], stream_id: str) -> int | None:
        """Find stream index by ID.
        
        Args:
            streams: List of stream dicts
            stream_id: UUID to search for
            
        Returns:
            Index if found, None otherwise
        """
        for i, stream in enumerate(streams):
            if stream.get("id") == stream_id:
                return i
        return None
    
    def _validate_unique_stream_name(
        self,
        streams: list[dict],
        name: str,
        exclude_index: int | None = None
    ) -> None:
        """Validate stream name is unique (case-insensitive).
        
        Args:
            streams: List of existing streams
            name: Name to validate
            exclude_index: Optional index to exclude (for updates)
            
        Raises:
            ValueError: If name already exists
        """
        normalized_name = normalize_stream_name(name)
        
        for i, stream in enumerate(streams):
            if exclude_index is not None and i == exclude_index:
                continue
            
            if normalize_stream_name(stream.get("name", "")) == normalized_name:
                raise ValueError(
                    f"Stream name '{name}' already exists (case-insensitive)"
                )