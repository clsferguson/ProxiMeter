"""Stream management service with FFmpeg process control.

Manages RTSP stream lifecycle with GPU-accelerated FFmpeg processing:
- Stream CRUD with YAML persistence
- FFmpeg subprocess management (start/stop)
- MJPEG frame piping from FFmpeg stdout
- Auto-start on creation and application boot
- Hardware acceleration (CUDA/NVDEC, ROCm, QSV)

FFmpeg Pipeline:
    RTSP → FFmpeg (GPU decode) → MJPEG stdout → Parse frames → Web/API

Constitution Compliance:
    - GPU-only operation (fail-fast if unavailable)
    - FFmpeg for ALL processing (no OpenCV VideoCapture)
    - 5fps cap enforced
    - Full resolution preserved
    - No video storage (live frames only)

Logging Strategy:
    DEBUG - Process details, buffer operations, frame parsing
    INFO  - Stream lifecycle, FFmpeg starts, auto-start
    WARN  - GPU unavailable, RTSP unreachable, process timeouts
    ERROR - FFmpeg failures, exceptions with stack traces
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, Final

from ..config_io import load_streams, save_streams, get_gpu_backend
from ..models.stream import Stream
from ..utils.validation import validate_rtsp_url as validate_rtsp_url_format
from ..utils.strings import normalize_stream_name, mask_rtsp_credentials
from ..utils.rtsp import probe_rtsp_stream, build_ffmpeg_command, validate_rtsp_url

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

DEFAULT_PROBE_TIMEOUT: Final[float] = 5.0
"""Timeout for RTSP stream connectivity probe."""

STREAM_STOP_TIMEOUT: Final[float] = 5.0
"""Graceful shutdown timeout before SIGKILL."""

FRAME_READ_TIMEOUT: Final[float] = 2.0
"""Timeout for reading single frame from FFmpeg stdout."""

JPEG_START_MARKER: Final[bytes] = b'\xff\xd8'
"""JPEG SOI (Start of Image) marker."""

JPEG_END_MARKER: Final[bytes] = b'\xff\xd9'
"""JPEG EOI (End of Image) marker."""

# ============================================================================
# Streams Service
# ============================================================================

class StreamsService:
    """Service for RTSP stream management with FFmpeg processing.
    
    Handles complete stream lifecycle:
    1. CRUD operations with YAML persistence
    2. FFmpeg subprocess management
    3. MJPEG frame piping and parsing
    4. Auto-start on creation/boot
    5. GPU acceleration coordination
    
    Attributes:
        active_processes: {stream_id: {"process": Process, "buffer": bytearray}}
        gpu_backend: Detected GPU (nvidia/amd/intel/none)
    """
    
    def __init__(self) -> None:
        """Initialize service and detect GPU backend.
        
        Note: Does not raise if GPU unavailable - individual stream starts
        will fail with clear error messages.
        """
        self.active_processes: dict[str, dict[str, Any]] = {}
        self.gpu_backend = get_gpu_backend()
        
        if self.gpu_backend == "none":
            logger.warning("No GPU detected - stream starts will fail")
        else:
            logger.info(f"StreamsService initialized: GPU={self.gpu_backend}")
    
    # ========================================================================
    # Stream Retrieval
    # ========================================================================
    
    async def list_streams(self) -> list[dict]:
        """List all configured streams sorted by display order."""
        try:
            config = load_streams()
            streams = config.get("streams", [])
            streams.sort(key=lambda s: s.get("order", 0))
            logger.debug(f"Listed {len(streams)} stream(s)")
            return streams
        except Exception as e:
            logger.error(f"Failed to list streams: {e}", exc_info=True)
            return []
    
    async def get_stream(self, stream_id: str) -> dict | None:
        """Get stream by ID."""
        try:
            config = load_streams()
            for stream in config.get("streams", []):
                if stream.get("id") == stream_id:
                    return stream
            logger.debug(f"Stream not found: {stream_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get stream {stream_id}: {e}", exc_info=True)
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
        auto_start: bool = True
    ) -> dict:
        """Create new stream with validation and optional auto-start.
        
        Args:
            name: Display name (1-50 chars)
            rtsp_url: RTSP stream URL
            hw_accel_enabled: Use GPU acceleration
            ffmpeg_params: Custom FFmpeg args (defaults applied if empty)
            auto_start: Auto-start on creation
            
        Returns:
            Created stream dict
            
        Raises:
            ValueError: Invalid name/URL
            RuntimeError: GPU required but unavailable
        """
        # Normalize
        name = name.strip()
        rtsp_url = rtsp_url.strip()
        
        # Validate GPU
        if hw_accel_enabled and self.gpu_backend == "none":
            raise RuntimeError("GPU acceleration unavailable")
        
        # Validate name
        if not name or len(name) > 50:
            raise ValueError("Name must be 1-50 characters")
        
        # Validate URL format
        is_valid, error_msg = validate_rtsp_url_format(rtsp_url)
        if not is_valid:
            raise ValueError(error_msg or "Invalid RTSP URL")
        
        # Apply defaults if no custom params
        if not ffmpeg_params:
            ffmpeg_params = self._get_default_ffmpeg_params(hw_accel_enabled)
            logger.debug(f"Applied default FFmpeg params for {self.gpu_backend}")
        else:
            logger.debug(f"Using {len(ffmpeg_params)} custom FFmpeg params")
        
        # Load config
        config = load_streams()
        streams = config.get("streams", [])
        
        # Check duplicate name
        self._validate_unique_stream_name(streams, name)
        
        # Probe connectivity
        logger.debug(f"Probing RTSP: {mask_rtsp_credentials(rtsp_url)}")
        is_reachable = await probe_rtsp_stream(rtsp_url, DEFAULT_PROBE_TIMEOUT)
        if not is_reachable:
            logger.warning(f"RTSP unreachable: {mask_rtsp_credentials(rtsp_url)}")
        
        # Create stream
        stream = Stream(
            id=str(uuid.uuid4()),
            name=name,
            rtsp_url=rtsp_url,
            hw_accel_enabled=hw_accel_enabled,
            ffmpeg_params=ffmpeg_params,
            auto_start=auto_start,
            created_at=datetime.now(timezone.utc).isoformat(),
            order=len(streams),
            status="stopped"
        )
        
        # Persist
        stream_dict = stream.model_dump()
        streams.append(stream_dict)
        config["streams"] = streams
        save_streams(config)
        
        logger.info(f"Created stream: {name} ({stream.id}, auto_start={auto_start})")
        
        # Auto-start if enabled
        if auto_start:
            logger.info(f"Auto-starting: {stream.id}")
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
        auto_start: bool | None = None
    ) -> dict | None:
        """Update stream (partial update)."""
        config = load_streams()
        streams = config.get("streams", [])
        
        # Find stream
        stream_index = self._find_stream_index(streams, stream_id)
        if stream_index is None:
            logger.debug(f"Update failed - not found: {stream_id}")
            return None
        
        stream = streams[stream_index]
        url_changed = False
        
        # Update name
        if name is not None:
            name = name.strip()
            if not name or len(name) > 50:
                raise ValueError("Name must be 1-50 characters")
            self._validate_unique_stream_name(streams, name, exclude_index=stream_index)
            stream["name"] = name
        
        # Update URL
        if rtsp_url is not None:
            rtsp_url = rtsp_url.strip()
            is_valid, error_msg = validate_rtsp_url_format(rtsp_url)
            if not is_valid:
                raise ValueError(error_msg or "Invalid RTSP URL")
            stream["rtsp_url"] = rtsp_url
            url_changed = True
        
        # Update HW accel
        if hw_accel_enabled is not None:
            if hw_accel_enabled and self.gpu_backend == "none":
                raise RuntimeError("GPU acceleration unavailable")
            stream["hw_accel_enabled"] = hw_accel_enabled
        
        # Update FFmpeg params (apply defaults if cleared)
        if ffmpeg_params is not None:
            if not ffmpeg_params:
                hw_accel = stream.get("hw_accel_enabled", True)
                stream["ffmpeg_params"] = self._get_default_ffmpeg_params(hw_accel)
                logger.debug(f"Applied default params: {stream_id}")
            else:
                stream["ffmpeg_params"] = ffmpeg_params
                logger.debug(f"Applied custom params: {stream_id}")
        
        # Update auto-start
        if auto_start is not None:
            stream["auto_start"] = auto_start
        
        # Re-probe if URL changed
        if url_changed:
            logger.debug(f"Re-probing: {stream_id}")
            is_reachable = await probe_rtsp_stream(stream["rtsp_url"], DEFAULT_PROBE_TIMEOUT)
            if not is_reachable:
                logger.warning(f"Updated URL unreachable: {stream_id}")
        
        # Update status
        if status is not None:
            stream["status"] = status
        
        # Persist
        config["streams"] = streams
        save_streams(config)
        
        logger.info(f"Updated stream: {stream_id}")
        return stream
    
    # ========================================================================
    # Stream Deletion
    # ========================================================================
    
    async def delete_stream(self, stream_id: str) -> bool:
        """Delete stream and stop if running."""
        # Stop if running
        if stream_id in self.active_processes:
            await self.stop_stream(stream_id)
        
        config = load_streams()
        streams = config.get("streams", [])
        
        # Remove
        initial_count = len(streams)
        streams = [s for s in streams if s.get("id") != stream_id]
        
        if len(streams) == initial_count:
            logger.debug(f"Delete failed - not found: {stream_id}")
            return False
        
        # Renumber orders
        for i, stream in enumerate(streams):
            stream["order"] = i
        
        config["streams"] = streams
        save_streams(config)
        
        logger.info(f"Deleted stream: {stream_id}")
        return True
    
    # ========================================================================
    # Stream Reordering
    # ========================================================================
    
    async def reorder_streams(self, order: list[str]) -> bool:
        """Reorder streams by ID list."""
        config = load_streams()
        streams = config.get("streams", [])
        
        # No-op for 0-1 streams
        if len(streams) <= 1:
            logger.debug("Reorder skipped: ≤1 streams")
            return True
        
        # Validate
        if len(order) != len(streams):
            raise ValueError(f"Order must contain {len(streams)} IDs")
        
        if len(set(order)) != len(order):
            raise ValueError("Duplicate IDs in order")
        
        # Build map
        stream_map = {s.get("id"): s for s in streams}
        
        # Validate IDs exist
        for stream_id in order:
            if stream_id not in stream_map:
                raise ValueError(f"Unknown stream ID: {stream_id}")
        
        # Check if already correct (idempotent)
        current_order = [s.get("id") for s in streams]
        if current_order == order:
            logger.debug("Reorder skipped: already correct")
            return True
        
        # Reorder
        reordered = []
        for i, stream_id in enumerate(order):
            stream = stream_map[stream_id].copy()
            stream["order"] = i
            reordered.append(stream)
        
        config["streams"] = reordered
        save_streams(config)
        
        logger.info(f"Reordered {len(reordered)} stream(s)")
        return True
    
    # ========================================================================
    # Auto-Start Support
    # ========================================================================
    
    async def auto_start_configured_streams(self) -> None:
        """Auto-start all streams with auto_start=True.
        
        Called on application startup to resume streams.
        """
        try:
            streams = await self.list_streams()
            auto_start_streams = [s for s in streams if s.get("auto_start", False)]
            
            if not auto_start_streams:
                logger.info("No streams configured for auto-start")
                return
            
            logger.info(f"Auto-starting {len(auto_start_streams)} stream(s)")
            
            for stream in auto_start_streams:
                stream_id = stream["id"]
                stream_name = stream.get("name", "Unknown")
                logger.debug(f"Queuing auto-start: {stream_name} ({stream_id})")
                asyncio.create_task(self.start_stream(stream_id, stream))
                
        except Exception as e:
            logger.error(f"Auto-start failed: {e}", exc_info=True)

    # ========================================================================
    # FFmpeg Process Control
    # ========================================================================
    
    async def start_stream(self, stream_id: str, stream: dict) -> bool:
        """Start FFmpeg processing with MJPEG piping.
        
        Starts FFmpeg subprocess to decode RTSP and pipe MJPEG frames.
        
        Args:
            stream_id: Stream UUID
            stream: Stream config dict
            
        Returns:
            True if started successfully
        """
        try:
            if stream_id in self.active_processes:
                logger.warning(f"Already running: {stream_id}")
                return True
            
            # Validate GPU
            if self.gpu_backend == "none":
                raise RuntimeError("GPU backend required")
            
            if stream.get("hw_accel_enabled") and self.gpu_backend == "none":
                raise ValueError("GPU acceleration unavailable")
            
            # Get params
            url = stream["rtsp_url"]
            params = stream.get("ffmpeg_params", [])
            hw_accel = stream.get("hw_accel_enabled", False)
            
            # Validate
            if not validate_rtsp_url(url, params, self.gpu_backend):
                raise ValueError("Invalid RTSP URL or params")
            
            # Build command
            cmd = build_ffmpeg_command(
                rtsp_url=url,
                ffmpeg_params=params,
                gpu_backend=self.gpu_backend if hw_accel else None
            )
            
            logger.info(f"Starting FFmpeg: {stream_id} ({mask_rtsp_credentials(url)})")
            logger.debug(f"GPU={self.gpu_backend}, HW_accel={hw_accel}, PID will be assigned")
            
            # Pre-register (prevents race condition in get_frame)
            self.active_processes[stream_id] = {
                "process": None,
                "buffer": bytearray(),
            }
            
            # Start subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Update with process
            self.active_processes[stream_id]["process"] = process
            logger.debug(f"FFmpeg started: PID={process.pid}")
            
            # Start stderr monitor
            asyncio.create_task(self._monitor_ffmpeg_stderr(stream_id, process))
            
            # Update config status
            config = load_streams()
            streams = config.get("streams", [])
            for s in streams:
                if s.get("id") == stream_id:
                    s["status"] = "running"
                    break
            config["streams"] = streams
            save_streams(config)
            
            # Wait for initialization
            await asyncio.sleep(0.5)
            
            # Check if died immediately
            if process.returncode is not None:
                stderr = await process.stderr.read() if process.stderr else b""
                error_msg = stderr.decode().strip()
                
                logger.error(f"FFmpeg died immediately: {stream_id}")
                logger.error(f"Return code: {process.returncode}")
                logger.error(f"FFmpeg stderr:\n{error_msg}")
                
                # Cleanup
                self.active_processes.pop(stream_id, None)
                
                # Update status
                config = load_streams()
                streams = config.get("streams", [])
                for s in streams:
                    if s.get("id") == stream_id:
                        s["status"] = "stopped"
                        break
                config["streams"] = streams
                save_streams(config)
                
                raise RuntimeError(f"FFmpeg failed (code {process.returncode})")
            
            logger.info(f"Stream started: {stream_id} (PID={process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start {stream_id}: {e}", exc_info=True)
            
            # Cleanup
            self.active_processes.pop(stream_id, None)
            
            # Update status
            try:
                config = load_streams()
                streams = config.get("streams", [])
                for s in streams:
                    if s.get("id") == stream_id:
                        s["status"] = "stopped"
                        break
                config["streams"] = streams
                save_streams(config)
            except Exception as config_err:
                logger.error(f"Failed to update status: {config_err}")
            
            return False
    
    async def stop_stream(self, stream_id: str) -> bool:
        """Stop FFmpeg processing gracefully."""
        if stream_id not in self.active_processes:
            logger.warning(f"Not running: {stream_id}")
            return False
        
        try:
            proc_data = self.active_processes.pop(stream_id)
            process = proc_data["process"]
            
            # Terminate
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=STREAM_STOP_TIMEOUT)
                logger.debug(f"FFmpeg terminated gracefully: {stream_id}")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout, killing: {stream_id}")
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
            
            logger.info(f"Stream stopped: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop {stream_id}: {e}", exc_info=True)
            return False
    
    # ========================================================================
    # Frame Access
    # ========================================================================
    
    async def get_frame(self, stream_id: str) -> tuple[bool, bytes] | None:
        """Get next MJPEG frame from FFmpeg stdout.
        
        Reads from FFmpeg stdout, parses JPEG markers, returns complete frame.
        
        Args:
            stream_id: Stream UUID
            
        Returns:
            (success, jpeg_bytes) if available, None if stream ended
        """
        if stream_id not in self.active_processes:
            logger.warning(f"Frame request for inactive stream: {stream_id}")
            return None
        
        proc_data = self.active_processes[stream_id]
        process = proc_data["process"]
        buffer = proc_data["buffer"]
        
        # Check if alive
        if process.returncode is not None:
            logger.error(f"FFmpeg dead (code {process.returncode}): {stream_id}")
            return None
        
        try:
            # Read until complete frame found
            max_attempts = 50
            
            for attempt in range(max_attempts):
                # Check buffer for complete frame
                start_idx = buffer.find(JPEG_START_MARKER)
                if start_idx != -1:
                    end_idx = buffer.find(JPEG_END_MARKER, start_idx + 2)
                    if end_idx != -1:
                        # Extract frame
                        jpeg_data = bytes(buffer[start_idx:end_idx + 2])
                        del buffer[:end_idx + 2]
                        
                        logger.debug(f"Frame extracted: {len(jpeg_data)} bytes")
                        return (True, jpeg_data)
                
                # Need more data
                try:
                    chunk = await asyncio.wait_for(
                        process.stdout.read(8192),
                        timeout=FRAME_READ_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    logger.debug(f"Read timeout (attempt {attempt + 1}/{max_attempts})")
                    continue
                
                if not chunk:
                    logger.error(f"FFmpeg stdout closed: {stream_id}")
                    return None
                
                buffer.extend(chunk)
                
                # Prevent unbounded growth (10MB limit)
                if len(buffer) > 10 * 1024 * 1024:
                    logger.warning(f"Buffer overflow, resetting: {stream_id}")
                    buffer[:] = buffer[-1024*1024:]
            
            # Max attempts reached
            logger.error(f"Failed to extract frame after {max_attempts} attempts: {stream_id}")
            return (False, b'')
                
        except Exception as e:
            logger.error(f"Frame read error for {stream_id}: {e}", exc_info=True)
            return None
    
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
                raise ValueError(f"Stream name '{name}' already exists")
    
    def _get_default_ffmpeg_params(self, hw_accel_enabled: bool) -> list[str]:
        """Get default FFmpeg parameters for GPU backend.
        
        Args:
            hw_accel_enabled: Include GPU acceleration flags
            
        Returns:
            List of FFmpeg parameter strings
        """
        # Base params (always applied)
        params = [
            '-hide_banner',
            '-loglevel', 'warning',
            '-threads', '2',
            '-rtsp_transport', 'tcp',
            '-rtsp_flags', 'prefer_tcp',
            '-max_delay', '500000',
            '-analyzeduration', '1000000',
            '-probesize', '1000000',
            '-fflags', 'nobuffer',
            '-flags', 'low_delay',
        ]
        
        # Add GPU params if enabled
        if hw_accel_enabled and self.gpu_backend != "none":
            if self.gpu_backend == "nvidia":
                params.extend([
                    '-hwaccel', 'cuda',
                    '-hwaccel_output_format', 'cuda',
                ])
            elif self.gpu_backend == "amd":
                params.extend([
                    '-hwaccel', 'vaapi',
                    '-hwaccel_device', '/dev/dri/renderD128',
                ])
            elif self.gpu_backend == "intel":
                params.extend([
                    '-hwaccel', 'qsv',
                    '-hwaccel_device', '/dev/dri/renderD128',
                ])
        
        return params
    
    async def _monitor_ffmpeg_stderr(
        self,
        stream_id: str,
        process: asyncio.subprocess.Process
    ) -> None:
        """Monitor FFmpeg stderr for errors and warnings.
        
        Runs as background task to continuously read FFmpeg output.
        """
        if process.stderr is None:
            logger.warning(f"FFmpeg stderr unavailable: {stream_id}")
            return
        
        try:
            while process.returncode is None:
                try:
                    line = await asyncio.wait_for(
                        process.stderr.readline(),
                        timeout=1.0
                    )
                    
                    if not line:
                        break
                    
                    message = line.decode().strip()
                    if not message:
                        continue
                    
                    # Log by severity
                    msg_lower = message.lower()
                    if 'error' in msg_lower or 'fatal' in msg_lower:
                        logger.error(f"FFmpeg [{stream_id}]: {message}")
                    elif 'warning' in msg_lower:
                        logger.warning(f"FFmpeg [{stream_id}]: {message}")
                    elif 'deprecated' in msg_lower:
                        logger.debug(f"FFmpeg [{stream_id}]: {message}")
                    else:
                        logger.debug(f"FFmpeg [{stream_id}]: {message}")
                        
                except asyncio.TimeoutError:
                    continue
                
        except asyncio.CancelledError:
            logger.debug(f"FFmpeg stderr monitor cancelled: {stream_id}")
        except Exception as e:
            logger.error(f"Stderr monitor error for {stream_id}: {e}")


logger.debug("StreamsService module loaded")