"""Stream management service with FFmpeg process control."""
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
STREAM_STOP_TIMEOUT: Final[float] = 5.0
MIN_FPS: Final[int] = 1
MAX_FPS: Final[int] = 30


# ============================================================================
# Streams Service
# ============================================================================

class StreamsService:
    """Service for managing RTSP streams with FFmpeg processing."""
    
    def __init__(self) -> None:
        """Initialize streams service."""
        self.active_processes: dict[str, dict[str, Any]] = {}
        self.gpu_backend = get_gpu_backend()
        logger.info(f"StreamsService initialized with GPU backend: {self.gpu_backend}")
    
    # ========================================================================
    # Stream Retrieval
    # ========================================================================
    
    async def list_streams(self) -> list[dict]:
        """List all configured streams sorted by order."""
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
        """Get a stream by ID."""
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
        target_fps: int = 5
    ) -> dict:
        """Create a new stream with validation."""
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
        
        # Create stream object
        stream = Stream(
            id=str(uuid.uuid4()),
            name=name,
            rtsp_url=rtsp_url,
            hw_accel_enabled=hw_accel_enabled,
            ffmpeg_params=ffmpeg_params if ffmpeg_params is not None else [],
            target_fps=target_fps,
            created_at=datetime.now(timezone.utc).isoformat(),
            order=len(streams),
            status="stopped"
        )
        
        # Persist
        streams.append(stream.model_dump())
        config["streams"] = streams
        save_streams(config)
        
        logger.info(f"Created stream {stream.id}: {name}")
        return stream.model_dump()
    
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
        target_fps: int | None = None
    ) -> dict | None:
        """Update a stream (partial update)."""
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
        """Delete a stream and stop it if running."""
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
        """Reorder streams by ID list."""
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
    # FFmpeg Process Control
    # ========================================================================
    
    async def start_stream(self, stream_id: str, stream: dict) -> bool:
        """Start FFmpeg processing for a stream."""
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
        """Stop FFmpeg processing for a stream."""
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
        """Get next frame from stream pipe."""
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
        """Find stream index by ID."""
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
        """Validate stream name is unique (case-insensitive)."""
        normalized_name = normalize_stream_name(name)
        
        for i, stream in enumerate(streams):
            if exclude_index is not None and i == exclude_index:
                continue
            
            if normalize_stream_name(stream.get("name", "")) == normalized_name:
                raise ValueError(
                    f"Stream name '{name}' already exists (case-insensitive)"
                )
