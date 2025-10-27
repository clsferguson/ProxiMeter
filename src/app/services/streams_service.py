"""Stream management service with FFmpeg process control.

This service manages the lifecycle of RTSP stream processing using FFmpeg:
- Creates and persists stream configurations
- Starts/stops FFmpeg processes for stream decoding with GPU acceleration
- Pipes MJPEG frames from FFmpeg stdout for web streaming and snapshots
- Auto-starts streams on application startup
- Coordinates hardware acceleration (CUDA/NVDEC, ROCm, Intel)

Constitution-compliant:
- GPU-only operation (no CPU fallback)
- FFmpeg for ALL stream processing
- 5fps cap enforced
- Full resolution preservation
- No video storage beyond live frames

Updated: Replaced OpenCV VideoCapture with direct FFmpeg MJPEG piping
for better GPU integration and constitution compliance.
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
"""Timeout in seconds for probing RTSP stream connectivity."""

STREAM_STOP_TIMEOUT: Final[float] = 5.0
"""Timeout in seconds for gracefully stopping FFmpeg process."""

FRAME_READ_TIMEOUT: Final[float] = 2.0
"""Timeout in seconds for reading a single frame from FFmpeg."""

JPEG_START_MARKER: Final[bytes] = b'\xff\xd8'
"""JPEG SOI (Start of Image) marker."""

JPEG_END_MARKER: Final[bytes] = b'\xff\xd9'
"""JPEG EOI (End of Image) marker."""


# ============================================================================
# Streams Service
# ============================================================================

class StreamsService:
    """Service for managing RTSP streams with FFmpeg processing.
    
    This service handles the complete lifecycle of stream processing:
    1. Configuration persistence (YAML file storage)
    2. FFmpeg subprocess management with GPU acceleration
    3. MJPEG frame piping from FFmpeg stdout
    4. Frame parsing for streaming and snapshots
    5. Auto-start on creation and application startup
    
    FFmpeg Pipeline:
    RTSP → FFmpeg (GPU decode) → MJPEG pipe → Parse frames → Web/API
    
    Constitution Compliance:
    - GPU backend required (fail-fast if missing)
    - FFmpeg handles ALL stream processing
    - 5fps default, configurable 1-30fps
    - No video storage (live frames only)
    
    Attributes:
        active_processes: Dict mapping stream_id to process info
        gpu_backend: Detected GPU backend (nvidia, amd, intel, none)
    """
    
    def __init__(self) -> None:
        """Initialize streams service and validate GPU backend.
        
        Raises:
            RuntimeError: If GPU backend is 'none' (constitution requirement)
        """
        self.active_processes: dict[str, dict[str, Any]] = {}
        self.gpu_backend = get_gpu_backend()
        
        # Constitution Principle III: GPU backend contract
        if self.gpu_backend == "none":
            logger.error("No GPU backend detected - application requires GPU acceleration")
            # Don't raise here, let individual stream starts fail with clear error
        else:
            logger.info(f"StreamsService initialized with GPU backend: {self.gpu_backend}")
    
    # ========================================================================
    # Stream Retrieval
    # ========================================================================
    
    async def list_streams(self) -> list[dict]:
        """List all configured streams sorted by display order."""
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
        auto_start: bool = True
    ) -> dict:
        """Create a new stream with validation and optional auto-start.
        
        Constitution Principle III: GPU backend validation on creation.
        
        Args:
            name: Display name for stream (1-50 characters)
            rtsp_url: RTSP URL to stream source
            hw_accel_enabled: Whether to use GPU hardware acceleration
            ffmpeg_params: Optional additional FFmpeg parameters (defaults applied if None/empty)
            target_fps: Target frame rate for processing (1-30)
            auto_start: Whether to automatically start stream on creation
            
        Returns:
            Created stream dict with all fields
            
        Raises:
            ValueError: If validation fails
            RuntimeError: If GPU required but not detected
        """
        # Normalize inputs
        name = name.strip()
        rtsp_url = rtsp_url.strip()
        
        # Validate GPU requirements
        if hw_accel_enabled and self.gpu_backend == "none":
            raise RuntimeError(
                "Hardware acceleration requested but no GPU detected. "
                "This application requires GPU acceleration (NVIDIA/AMD/Intel)."
            )
        
        # Validate name
        if not name or len(name) > 50:
            raise ValueError("Stream name must be 1-50 characters")
        
        # Validate RTSP URL format
        is_valid, error_msg = validate_rtsp_url_format(rtsp_url)
        if not is_valid:
            raise ValueError(error_msg or "Invalid RTSP URL")
        
        # Apply default FFmpeg params if none provided
        # This ensures GPU acceleration flags are included when user leaves field empty
        if not ffmpeg_params or len(ffmpeg_params) == 0:
            ffmpeg_params = self._get_default_ffmpeg_params(hw_accel_enabled)
            logger.info(f"Applying default FFmpeg params for {self.gpu_backend} backend")
            logger.debug(f"Applied default FFmpeg params: {ffmpeg_params}") 
        else:
            logger.info(f"Using custom FFmpeg params: {' '.join(ffmpeg_params)}")
            logger.debug(f"Using custom FFmpeg params: {ffmpeg_params}")
        
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
            ffmpeg_params=ffmpeg_params,
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
        auto_start: bool | None = None
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
            if hw_accel_enabled and self.gpu_backend == "none":
                raise RuntimeError("Hardware acceleration unavailable (no GPU detected)")
            stream["hw_accel_enabled"] = hw_accel_enabled
        
        # Update FFmpeg params - apply defaults if explicitly set to empty
        if ffmpeg_params is not None:
            if len(ffmpeg_params) == 0:
                # User cleared the field - apply defaults
                hw_accel = stream.get("hw_accel_enabled", True)
                stream["ffmpeg_params"] = self._get_default_ffmpeg_params(hw_accel)
                logger.info(f"Applied default FFmpeg params for stream {stream_id}")
            else:
                # User provided custom params
                stream["ffmpeg_params"] = ffmpeg_params
                logger.info(f"Applied custom FFmpeg params for stream {stream_id}")
        
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
    # Auto-Start Support
    # ========================================================================
    
    async def auto_start_configured_streams(self) -> None:
        """Auto-start all streams with auto_start=True.
        
        Called on application startup to resume previously running streams.
        Constitution Principle II: Auto-start for continuous monitoring.
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
        """Start FFmpeg processing for a stream with MJPEG piping.
        
        Starts FFmpeg subprocess to decode RTSP stream and pipe MJPEG frames
        to stdout for web streaming and snapshots.
        
        Constitution compliance:
        - GPU backend required (fail-fast)
        - FFmpeg for all stream processing
        - 5fps cap enforced
        - Full resolution preserved
        
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
            
            # Constitution Principle III: GPU backend validation
            if self.gpu_backend == "none":
                raise RuntimeError(
                    "Cannot start stream: No GPU backend detected. "
                    "This application requires GPU acceleration."
                )
            
            # Validate GPU requirements
            if stream.get("hw_accel_enabled") and self.gpu_backend == "none":
                raise ValueError("Hardware acceleration unavailable (no GPU detected)")
            
            # Get parameters
            url = stream["rtsp_url"]
            params = stream.get("ffmpeg_params", [])
            hw_accel = stream.get("hw_accel_enabled", False)
            
            # Validate
            if not validate_rtsp_url(url, params, self.gpu_backend):
                raise ValueError("Invalid RTSP URL or FFmpeg params")

            # Build command (FFmpeg pipes MJPEG to stdout)
            cmd = build_ffmpeg_command(
                rtsp_url=url,
                ffmpeg_params=params,
                gpu_backend=self.gpu_backend if hw_accel else None
            )
            
            logger.info(f"Starting FFmpeg for {stream_id}: {mask_rtsp_credentials(url)}")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            logger.debug(f"GPU backend: {self.gpu_backend}, HW accel: {hw_accel}")

            # Start subprocess with stdout pipe
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.debug(f"FFmpeg process started with PID: {process.pid}")

            # Wait a moment for process to initialize
            await asyncio.sleep(1.0)
            
            # Check if process died immediately
            if process.returncode is not None:
                # Read ALL stderr output
                stderr = await process.stderr.read() if process.stderr else b""
                error_msg = stderr.decode().strip()
                
                # Log the full FFmpeg error
                logger.error(f"❌ FFmpeg died immediately for {stream_id}")
                logger.error(f"FFmpeg return code: {process.returncode}")
                logger.error(f"FFmpeg stderr output:\n{error_msg}")
                
                # Also print to console to bypass any logging filters
                print(f"\n{'='*80}", flush=True)
                print(f"❌ FFMPEG FAILED FOR STREAM: {stream_id}", flush=True)
                print(f"Return Code: {process.returncode}", flush=True)
                print(f"Error Output:", flush=True)
                print(error_msg, flush=True)
                print(f"{'='*80}\n", flush=True)
                
                raise RuntimeError(f"FFmpeg failed to start (code {process.returncode}): {error_msg}")
            
            # FFmpeg started successfully - create background task to monitor stderr
            asyncio.create_task(self._monitor_ffmpeg_stderr(stream_id, process))
            
            # Store process info
            self.active_processes[stream_id] = {
                "process": process,
                "buffer": bytearray(),
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
            
            logger.info(f"✅ Successfully started stream {stream_id} (PID: {process.pid}, GPU: {self.gpu_backend})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start stream {stream_id}: {e}", exc_info=True)
            
            # Cleanup on failure
            if stream_id in self.active_processes:
                self.active_processes.pop(stream_id)
            
            return False
    
    async def stop_stream(self, stream_id: str) -> bool:
        """Stop FFmpeg processing for a stream.
        
        Terminates FFmpeg process gracefully with fallback to kill.
        """
        if stream_id not in self.active_processes:
            logger.warning(f"Stream {stream_id} not running")
            return False
        
        try:
            proc_data = self.active_processes.pop(stream_id)
            process = proc_data["process"]
            
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
    
    # ========================================================================
    # Frame Access
    # ========================================================================
    
    async def get_frame(self, stream_id: str) -> tuple[bool, bytes] | None:
        """Get next MJPEG frame from FFmpeg stdout pipe.
        
        Reads from FFmpeg stdout, parses JPEG markers, and returns complete
        JPEG frame. This is used for both MJPEG streaming and snapshots.
        
        Constitution Principle II: Live frames only, no storage.
        
        Args:
            stream_id: UUID of stream to read from
            
        Returns:
            Tuple of (success, jpeg_bytes) if frame available, None otherwise
        """
        if stream_id not in self.active_processes:
            return None
        
        proc_data = self.active_processes[stream_id]
        process = proc_data["process"]
        buffer = proc_data["buffer"]
        
        try:
            # Keep reading until we have a complete frame
            max_attempts = 50  # Prevent infinite loop
            attempts = 0
            
            while attempts < max_attempts:
                attempts += 1
                
                # Check if we already have a complete frame in buffer
                start_idx = buffer.find(JPEG_START_MARKER)
                if start_idx != -1:
                    end_idx = buffer.find(JPEG_END_MARKER, start_idx + 2)
                    if end_idx != -1:
                        # Extract complete JPEG frame
                        jpeg_data = bytes(buffer[start_idx:end_idx + 2])
                        
                        # Remove processed data from buffer
                        del buffer[:end_idx + 2]
                        
                        logger.debug(f"Extracted frame: {len(jpeg_data)} bytes")
                        return (True, jpeg_data)
                
                # Need more data - read chunk from stdout
                try:
                    chunk = await asyncio.wait_for(
                        process.stdout.read(8192),  # Increased chunk size
                        timeout=0.5  # Shorter timeout for faster retries
                    )
                except asyncio.TimeoutError:
                    # No data yet, continue trying
                    continue
                
                if not chunk:
                    logger.warning(f"FFmpeg stdout closed for stream {stream_id}")
                    return None
                
                # Append to buffer
                buffer.extend(chunk)
                
                # Prevent buffer from growing unbounded (10MB limit)
                if len(buffer) > 10 * 1024 * 1024:
                    logger.warning(f"Buffer overflow for stream {stream_id}, resetting")
                    # Keep last 1MB of data
                    buffer[:] = buffer[-1024*1024:]
            
            # Max attempts reached without finding frame
            logger.warning(f"Failed to extract frame after {max_attempts} attempts for stream {stream_id}")
            return (False, b'')
                
        except Exception as e:
            logger.error(f"Error reading frame from stream {stream_id}: {e}", exc_info=True)
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
                raise ValueError(
                    f"Stream name '{name}' already exists (case-insensitive)"
                )

    def _get_default_ffmpeg_params(self, hw_accel_enabled: bool) -> list[str]:
        """Get default FFmpeg parameters based on GPU backend.
        
        Applies GPU-specific hardware acceleration flags if enabled.
        These defaults match the frontend placeholder text.
        
        Args:
            hw_accel_enabled: Whether to include GPU acceleration flags
            
        Returns:
            List of FFmpeg parameter strings
        """
        # Base parameters (always applied)
        params = [
            '-hide_banner',
            '-loglevel', 'warning',
            '-threads', '2',
            '-rtsp_transport', 'tcp',
            '-stimeout', '5000000',
        ]
        
        # Add GPU-specific parameters if hardware acceleration enabled
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
    
    async def _monitor_ffmpeg_stderr(self, stream_id: str, process: asyncio.subprocess.Process) -> None:
        """Monitor FFmpeg stderr for errors and warnings.
        
        Runs as background task to continuously read and log FFmpeg output.
        """
        # Check if stderr is available
        if process.stderr is None:
            logger.warning(f"FFmpeg stderr not available for monitoring stream {stream_id}")
            return
        
        try:
            while process.returncode is None:
                # Read stderr line by line
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
                    
                    # Log FFmpeg messages at appropriate levels
                    if 'error' in message.lower() or 'fatal' in message.lower():
                        logger.error(f"FFmpeg [{stream_id}]: {message}")
                    elif 'warning' in message.lower():
                        logger.warning(f"FFmpeg [{stream_id}]: {message}")
                    elif 'deprecated' in message.lower():
                        logger.debug(f"FFmpeg [{stream_id}]: {message}")
                    else:
                        # Info/debug messages
                        logger.debug(f"FFmpeg [{stream_id}]: {message}")
                        
                except asyncio.TimeoutError:
                    # No output yet, continue monitoring
                    continue
                
        except asyncio.CancelledError:
            logger.debug(f"FFmpeg stderr monitor cancelled for {stream_id}")
        except Exception as e:
            logger.error(f"Error monitoring FFmpeg stderr for {stream_id}: {e}")