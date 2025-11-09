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
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Final

from ..config.ffmpeg_defaults import get_default_ffmpeg_params
from ..config_io import load_streams, save_streams, get_gpu_backend
from ..models.stream import Stream
from ..utils.validation import validate_rtsp_url as validate_rtsp_url_format
from ..utils.strings import normalize_stream_name, mask_rtsp_credentials
from ..utils.rtsp import probe_rtsp_stream, build_ffmpeg_command, validate_rtsp_url
from .motion import MotionDetector, ObjectTracker
from .. import metrics  # T067: Prometheus metrics

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
        self.active_processes_lock = asyncio.Lock()
        # T058-T061: Track viewer preferences for visualization toggles
        # {stream_id: {"count": int, "show_motion": bool, "show_tracking": bool}}
        self.active_mjpeg_viewers: dict[str, dict[str, Any]] = {}
        self.gpu_backend = get_gpu_backend()

        if self.gpu_backend == "none":
            logger.warning("No GPU detected - stream starts will fail")
        else:
            logger.info(f"StreamsService initialized: GPU={self.gpu_backend}")
    
    # ========================================================================
    # MJPEG Viewer Tracking
    # ========================================================================

    def register_mjpeg_viewer(
        self,
        stream_id: str,
        show_motion: bool = True,
        show_tracking: bool = True
    ) -> None:
        """Register an MJPEG viewer connection with visualization preferences (T058-T061).

        Args:
            stream_id: Stream identifier
            show_motion: Show red boxes around motion regions
            show_tracking: Show green/yellow boxes with IDs for tracked objects
        """
        if stream_id not in self.active_mjpeg_viewers:
            self.active_mjpeg_viewers[stream_id] = {
                "count": 0,
                "show_motion": show_motion,
                "show_tracking": show_tracking
            }

        self.active_mjpeg_viewers[stream_id]["count"] += 1
        # Update preferences to latest viewer's settings
        self.active_mjpeg_viewers[stream_id]["show_motion"] = show_motion
        self.active_mjpeg_viewers[stream_id]["show_tracking"] = show_tracking

        logger.info(
            f"[{stream_id}] MJPEG viewer connected "
            f"(total: {self.active_mjpeg_viewers[stream_id]['count']}, "
            f"motion={show_motion}, tracking={show_tracking})"
        )

    def unregister_mjpeg_viewer(self, stream_id: str) -> None:
        """Unregister an MJPEG viewer connection."""
        if stream_id in self.active_mjpeg_viewers:
            self.active_mjpeg_viewers[stream_id]["count"] -= 1
            if self.active_mjpeg_viewers[stream_id]["count"] <= 0:
                del self.active_mjpeg_viewers[stream_id]
                logger.info(f"[{stream_id}] Last MJPEG viewer disconnected")
            else:
                logger.info(
                    f"[{stream_id}] MJPEG viewer disconnected "
                    f"(remaining: {self.active_mjpeg_viewers[stream_id]['count']})"
                )

    def has_mjpeg_viewers(self, stream_id: str) -> bool:
        """Check if stream has active MJPEG viewers."""
        viewer_data = self.active_mjpeg_viewers.get(stream_id)
        return viewer_data is not None and viewer_data.get("count", 0) > 0

    def get_viewer_preferences(self, stream_id: str) -> tuple[bool, bool]:
        """Get visualization preferences for stream viewers (T058-T061).

        Returns:
            Tuple of (show_motion, show_tracking). Defaults to (True, True) if no viewers.
        """
        viewer_data = self.active_mjpeg_viewers.get(stream_id)
        if viewer_data is None:
            return (True, True)
        return (
            viewer_data.get("show_motion", True),
            viewer_data.get("show_tracking", True)
        )

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
            ffmpeg_params=ffmpeg_params,
            created_at=datetime.now(timezone.utc).isoformat(),
            order=len(streams),
            status="stopped"
        )
        
        # Persist
        stream_dict = stream.model_dump()
        streams.append(stream_dict)
        config["streams"] = streams
        save_streams(config)
        
        logger.info(f"Created stream: {name} ({stream.id})")

        # Always start stream (person detection requires it)
        logger.info(f"Starting stream: {stream.id}")
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
        
        # Update FFmpeg params (apply defaults if cleared)
        if ffmpeg_params is not None:
            if not ffmpeg_params:
                hw_accel = stream.get("hw_accel_enabled", True)
                stream["ffmpeg_params"] = self._get_default_ffmpeg_params(hw_accel)
                logger.debug(f"Applied default params: {stream_id}")
            else:
                stream["ffmpeg_params"] = ffmpeg_params
                logger.debug(f"Applied custom params: {stream_id}")

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
    
    async def start_all_streams(self) -> None:
        """Start all configured streams on application startup.
        
        Person detection requires streams to be running, so all streams
        are automatically started when the application boots.
        """
        try:
            streams = await self.list_streams()
            
            if not streams:
                logger.info("No streams configured")
                return
            
            logger.info(f"Starting {len(streams)} configured stream(s)")
            
            for stream in streams:
                stream_id = stream["id"]
                stream_name = stream.get("name", "Unknown")
                logger.debug(f"Queuing stream start: {stream_name} ({stream_id})")
                asyncio.create_task(self.start_stream(stream_id, stream))
                
        except Exception as e:
            logger.error(f"Stream startup failed: {e}", exc_info=True)


    # ========================================================================
    # Continuous Frame Processing (Background Task)
    # ========================================================================

    async def _continuous_frame_processor(self, stream_id: str) -> None:
        """Continuously read frames, run detection, and store latest frame.

        This prevents buffer accumulation and ensures detection runs
        even when no one is viewing the stream (fixes B1 and B2).

        Pipeline (T014-T017):
        1. Read raw BGR24 frame from FFmpeg stdout
        2. Extract motion regions using MotionDetector (T014)
        3. Run region-based YOLO detection (T015)
        4. OR: Run full-frame detection after 300s no-motion timeout (T016)
        5. Report detections (logs/metrics) (T017)
        6. IF viewers connected: render bounding boxes, store annotated frame
        7. ELSE: discard frame (no rendering/storage needed)
        8. Sleep to maintain 5 FPS
        """
        import numpy as np
        import cv2
        import time
        from ..api.detection import get_onnx_session, get_yolo_config_singleton
        from ..services.detection import (
            preprocess_frame, preprocess_region, run_inference, parse_detections,
            filter_detections, render_bounding_boxes, map_detections_to_frame,
            render_motion_boxes, render_tracking_boxes
        )
        from ..models.motion import ObjectState

        logger.info(f"[{stream_id}] Starting continuous frame processor")

        while stream_id in self.active_processes:
            try:
                proc_data = self.active_processes[stream_id]
                process = proc_data["process"]
                buffer = proc_data["buffer"]
                dimensions = proc_data.get("stream_dimensions")

                if not dimensions:
                    logger.error(f"[{stream_id}] No dimensions available")
                    await asyncio.sleep(1.0)
                    continue

                if process.returncode is not None:
                    logger.warning(f"[{stream_id}] FFmpeg process ended (code {process.returncode})")
                    break

                pipeline_start = time.perf_counter()
                width, height = dimensions
                frame_size = width * height * 3  # BGR = 3 bytes per pixel

                # Read raw frame bytes
                read_start = time.perf_counter()
                while len(buffer) < frame_size:
                    try:
                        chunk = await asyncio.wait_for(
                            process.stdout.read(frame_size - len(buffer)),
                            timeout=FRAME_READ_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        logger.debug(f"[{stream_id}] Timeout waiting for frame data")
                        break

                    if not chunk:
                        logger.error(f"[{stream_id}] FFmpeg stdout closed")
                        return

                    buffer.extend(chunk)

                if len(buffer) < frame_size:
                    # Not enough data, try again
                    await asyncio.sleep(0.05)
                    continue

                read_time_ms = (time.perf_counter() - read_start) * 1000

                # Extract frame bytes
                frame_bytes = bytes(buffer[:frame_size])
                del buffer[:frame_size]

                # Convert to NumPy array (make writable copy for OpenCV to draw on)
                frame_bgr = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((height, width, 3)).copy()

                # Run motion-based detection pipeline (T014-T017)
                try:
                    onnx_session = get_onnx_session()
                    if onnx_session is None:
                        logger.warning(f"[{stream_id}] ONNX session not available")
                        await asyncio.sleep(0.2)
                        continue

                    detection_config = proc_data.get("detection_config", {})
                    enabled_labels = detection_config.get("enabled_labels", ["person"])
                    min_confidence = detection_config.get("min_confidence", 0.8)

                    # Get YOLO model image size
                    yolo_config = get_yolo_config_singleton()
                    if yolo_config is None:
                        logger.error(f"[{stream_id}] YOLO config not available")
                        await asyncio.sleep(0.2)
                        continue

                    target_size = yolo_config.image_size

                    # Get motion detector and lock (T014)
                    motion_detector = proc_data.get("motion_detector")
                    motion_lock = proc_data.get("motion_lock")
                    last_motion_timestamp = proc_data.get("last_motion_timestamp")

                    # Track timing metrics (T017)
                    motion_start = time.perf_counter()
                    all_detections = []

                    # Step 2: Extract motion regions (T014)
                    # T081: Background subtractor error handling
                    MAX_CONSECUTIVE_ERRORS = 50  # Stop stream after 50 consecutive errors (10s at 5 FPS)
                    try:
                        with motion_lock:  # FR-024, FR-031: atomic motion state access
                            motion_regions = motion_detector.extract_motion_regions(
                                frame_bgr,
                                timestamp=time.time()
                            )
                        # Reset error count on success
                        proc_data["motion_error_count"] = 0

                    except cv2.error as e:
                        proc_data["motion_error_count"] += 1
                        logger.error(
                            f"[{stream_id}] OpenCV background subtractor error ({proc_data['motion_error_count']}/{MAX_CONSECUTIVE_ERRORS}): {e}. "
                            f"Frame shape: {frame_bgr.shape}, dtype: {frame_bgr.dtype}"
                        )

                        # Stop stream if too many consecutive errors
                        if proc_data["motion_error_count"] >= MAX_CONSECUTIVE_ERRORS:
                            logger.critical(
                                f"[{stream_id}] Stopping stream due to {MAX_CONSECUTIVE_ERRORS} consecutive motion detection errors"
                            )
                            asyncio.create_task(self.stop_stream(stream_id))
                            break  # Exit frame processing loop

                        motion_regions = []  # Fallback: treat as no motion

                    except Exception as e:
                        proc_data["motion_error_count"] += 1
                        logger.error(
                            f"[{stream_id}] Motion detection error ({proc_data['motion_error_count']}/{MAX_CONSECUTIVE_ERRORS}): {e}. "
                            f"Frame shape: {frame_bgr.shape}, dtype: {frame_bgr.dtype}",
                            exc_info=True
                        )

                        # Stop stream if too many consecutive errors
                        if proc_data["motion_error_count"] >= MAX_CONSECUTIVE_ERRORS:
                            logger.critical(
                                f"[{stream_id}] Stopping stream due to {MAX_CONSECUTIVE_ERRORS} consecutive motion detection errors"
                            )
                            asyncio.create_task(self.stop_stream(stream_id))
                            break  # Exit frame processing loop

                        motion_regions = []  # Fallback: treat as no motion

                    motion_time_ms = (time.perf_counter() - motion_start) * 1000

                    # Step 3: Collect regions for YOLO inference (T015 + T048-T050)
                    # Regions include: (1) motion regions, (2) stationary object regions (at reduced frequency)
                    yolo_start = time.perf_counter()
                    regions_to_process = []

                    # Get object tracker for stationary object check (BUG FIX: must retrieve before use)
                    object_tracker = proc_data.get("object_tracker")

                    # 3a: Add motion regions
                    if motion_regions:
                        # Update last motion timestamp
                        proc_data["last_motion_timestamp"] = time.time()
                        logger.debug(f"[{stream_id}] {len(motion_regions)} motion regions detected")

                        # Add all motion regions to processing list
                        for region in motion_regions:
                            regions_to_process.append(("motion", region.bounding_box, region.width, region.height))

                    # 3b: Add stationary object regions (T048-T050)
                    # Check if stationary objects need detection (every 50 frames = 10 seconds at 5 FPS)
                    current_frame = proc_data.get("frame_count", 0)
                    if object_tracker:
                        stationary_objects = object_tracker.get_stationary_objects()
                        for track in stationary_objects:
                            if track.should_run_detection(current_frame):
                                # Add stationary object bounding box as a region
                                x, y, w, h = track.bounding_box
                                regions_to_process.append(("stationary", (x, y, w, h), w, h))
                                logger.debug(
                                    f"[{stream_id}] Adding stationary object {track.id.hex[:8]} "
                                    f"for reduced-frequency detection (frame {current_frame})"
                                )

                    # TEMPORARY: Run YOLO on full frame (region-based detection has coordinate mapping bugs)
                    # Motion detection still runs for visualization, but YOLO uses full frame
                    # TODO: Fix coordinate mapping in preprocess_region/map_detections_to_frame
                    if motion_regions or regions_to_process:
                        logger.debug(f"[{stream_id}] Motion detected - running full-frame YOLO (region mode disabled)")

                        # Run full-frame YOLO inference
                        preprocessed, scale, padding = preprocess_frame(frame_bgr, target_size=target_size)
                        outputs = run_inference(onnx_session, preprocessed)
                        all_detections = parse_detections(outputs, scale, padding, (height, width))

                    # 3d: No-motion fallback (only if no motion detected)
                    if not motion_regions and not regions_to_process:
                        # Step 4: No-motion fallback logic (T016)
                        # Run full-frame detection after 300 seconds (5 min) of no motion
                        current_time = time.time()
                        should_run_fallback = False

                        if last_motion_timestamp is None:
                            # First frame with no motion - initialize timer
                            proc_data["last_motion_timestamp"] = current_time
                        elif (current_time - last_motion_timestamp) >= 300:
                            # 300 seconds (5 min) without motion - run full-frame check
                            should_run_fallback = True
                            # Reset timer for next 300-second interval
                            proc_data["last_motion_timestamp"] = current_time
                            logger.info(f"[{stream_id}] No motion for 300s - running full-frame fallback detection")

                        if should_run_fallback:
                            # Run full-frame YOLO inference
                            preprocessed, scale, padding = preprocess_frame(frame_bgr, target_size=target_size)
                            outputs = run_inference(onnx_session, preprocessed)
                            all_detections = parse_detections(outputs, scale, padding, (height, width))
                        else:
                            logger.debug(f"[{stream_id}] No motion detected, no fallback needed yet")

                    yolo_time_ms = (time.perf_counter() - yolo_start) * 1000

                    # Filter detections
                    filtered_detections = filter_detections(all_detections, enabled_labels, min_confidence)

                    # Step 5: Update object tracker with filtered detections (T040-T041)
                    tracking_start = time.perf_counter()
                    tracked_objects = []

                    # BUG FIX: Increment frame counter unconditionally (every frame, not just when detections exist)
                    # This ensures stationary object timing works correctly
                    proc_data["frame_count"] += 1
                    current_frame = proc_data["frame_count"]

                    if object_tracker:
                        # Convert Detection objects to (bbox, class_name, confidence) tuples
                        # Note: Detection.bbox is (x1, y1, x2, y2), but tracker expects (x, y, w, h)
                        detection_tuples = []
                        for det in filtered_detections:
                            x1, y1, x2, y2 = det.bbox
                            bbox_xywh = (x1, y1, x2 - x1, y2 - y1)  # Convert to (x, y, width, height)
                            detection_tuples.append((bbox_xywh, det.class_name, det.confidence))

                        # BUG FIX: Always update tracker, even with empty detections
                        # This ensures unmatched tracks are aged properly and eventually deleted
                        tracked_objects = object_tracker.update(detection_tuples, current_frame)

                    tracking_time_ms = (time.perf_counter() - tracking_start) * 1000

                    # Report detections and timing metrics (T017, T041)
                    if filtered_detections:
                        logger.info(
                            f"[{stream_id}] Detected {len(filtered_detections)} objects | "
                            f"Tracked: {len(tracked_objects)} | "
                            f"Motion: {motion_time_ms:.1f}ms, YOLO: {yolo_time_ms:.1f}ms, Tracking: {tracking_time_ms:.1f}ms | "
                            f"Regions: {len(motion_regions) if motion_regions else 0}"
                        )
                    else:
                        logger.debug(
                            f"[{stream_id}] No objects detected | "
                            f"Tracked: {len(tracked_objects)} | "
                            f"Motion: {motion_time_ms:.1f}ms, YOLO: {yolo_time_ms:.1f}ms, Tracking: {tracking_time_ms:.1f}ms | "
                            f"Regions: {len(motion_regions) if motion_regions else 0}"
                        )

                    # Conditional rendering based on viewer presence (B6 optimization, T059-T061)
                    has_viewers = self.has_mjpeg_viewers(stream_id)
                    if has_viewers:
                        # Get viewer visualization preferences (T058-T061)
                        show_motion, show_tracking = self.get_viewer_preferences(stream_id)

                        # Render visualization layers based on preferences
                        # Layer 1: Original YOLO detections (always shown)
                        render_bounding_boxes(frame_bgr, filtered_detections)

                        # Layer 2: Motion boxes (red, thin) - conditional (T059)
                        if show_motion and motion_regions:
                            render_motion_boxes(frame_bgr, motion_regions)

                        # Layer 3: Tracking boxes (green/yellow, with IDs) - conditional (T060-T061)
                        # Filter to only show ACTIVE and STATIONARY tracks (not TENTATIVE or LOST)
                        if show_tracking and tracked_objects:
                            visible_tracks = [
                                obj for obj in tracked_objects
                                if obj.state in (ObjectState.ACTIVE, ObjectState.STATIONARY)
                            ]
                            if visible_tracks:
                                render_tracking_boxes(frame_bgr, visible_tracks)

                        proc_data["latest_frame"] = frame_bgr
                        proc_data["latest_frame_time"] = time.time()
                    else:
                        # No viewers - skip rendering to save CPU/GPU
                        proc_data["latest_frame"] = None
                        logger.debug(f"[{stream_id}] Skipping rendering - no viewers")

                    total_time_ms = (time.perf_counter() - pipeline_start) * 1000
                    logger.debug(
                        f"[{stream_id}] Pipeline: {total_time_ms:.1f}ms total | "
                        f"Motion: {motion_time_ms:.1f}ms, YOLO: {yolo_time_ms:.1f}ms, Tracking: {tracking_time_ms:.1f}ms | "
                        f"{len(filtered_detections)} detections, {len(tracked_objects)} tracked"
                    )

                    # T067: Record Prometheus metrics
                    metrics.motion_detection_duration_seconds.labels(stream_id=stream_id).observe(motion_time_ms / 1000.0)
                    metrics.yolo_inference_duration_seconds.labels(stream_id=stream_id).observe(yolo_time_ms / 1000.0)
                    metrics.tracking_duration_seconds.labels(stream_id=stream_id).observe(tracking_time_ms / 1000.0)
                    metrics.motion_regions_detected.labels(stream_id=stream_id).set(len(motion_regions) if motion_regions else 0)

                    # Record tracked objects by state
                    if tracked_objects:
                        from ..models.motion import ObjectState
                        state_counts = {state.value: 0 for state in ObjectState}
                        for obj in tracked_objects:
                            state_counts[obj.state.value] += 1
                        for state, count in state_counts.items():
                            metrics.tracked_objects_total.labels(stream_id=stream_id, state=state).set(count)
                    else:
                        # Reset all state counts to 0
                        from ..models.motion import ObjectState
                        for state in ObjectState:
                            metrics.tracked_objects_total.labels(stream_id=stream_id, state=state.value).set(0)
                        state_counts = {state.value: 0 for state in ObjectState}

                    # Create and store MotionDetectionMetrics for SSE streaming
                    from ..models.motion import MotionDetectionMetrics
                    proc_data["motion_metrics"] = MotionDetectionMetrics(
                        stream_id=stream_id,
                        motion_regions_count=len(motion_regions) if motion_regions else 0,
                        tracked_objects_count=state_counts.get("active", 0) + state_counts.get("tentative", 0),
                        stationary_objects_count=state_counts.get("stationary", 0),
                        lost_objects_count=state_counts.get("lost", 0),
                        motion_detection_ms=motion_time_ms,
                        yolo_inference_ms=yolo_time_ms,
                        tracking_ms=tracking_time_ms,
                        total_frame_time_ms=total_time_ms,
                        timestamp=time.time()
                    )

                except Exception as e:
                    logger.error(f"[{stream_id}] Detection pipeline error: {e}", exc_info=True)

                # Maintain 5 FPS (200ms per frame)
                elapsed = time.perf_counter() - pipeline_start
                if elapsed < 0.2:
                    await asyncio.sleep(0.2 - elapsed)

            except asyncio.CancelledError:
                logger.info(f"[{stream_id}] Frame processor cancelled")
                break
            except Exception as e:
                logger.error(f"[{stream_id}] Frame processor error: {e}", exc_info=True)
                await asyncio.sleep(0.1)

        logger.info(f"[{stream_id}] Frame processor stopped")

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
            
            # Validate
            if not validate_rtsp_url(url, params, self.gpu_backend):
                raise ValueError("Invalid RTSP URL or params")

            # Detection is ALWAYS enabled - this is the core purpose of the app
            detection_config = stream.get("detection", {})
            logger.info(f"[{stream_id}] Detection active: labels={detection_config.get('enabled_labels', ['person'])}, min_conf={detection_config.get('min_confidence', 0.7)}")

            # Build command (detection always enabled)
            cmd = build_ffmpeg_command(
                rtsp_url=url,
                ffmpeg_params=params,
                gpu_backend=self.gpu_backend,
                detection_enabled=True  # Always True - detection is the core purpose
            )
            
            logger.info(f"Starting FFmpeg: {stream_id} ({mask_rtsp_credentials(url)})")
            logger.debug(f"GPU={self.gpu_backend}, PID will be assigned")
            
            # Initialize motion detector (T013)
            motion_detector = MotionDetector(
                history=500,
                var_threshold=16,
                detect_shadows=True,
                learning_rate=0.005,
                min_contour_area=500,
                merge_distance_threshold=40,
                nms_iou_threshold=0.4
            )
            logger.info(f"[{stream_id}] MotionDetector initialized")

            # Initialize object tracker (T039)
            # Frigate-style tracking: lower IoU threshold for better motion tracking
            # Reduced min_hits so tracks become ACTIVE faster (less tentative clutter)
            object_tracker = ObjectTracker(
                max_age=60,
                min_hits=2,
                iou_threshold=0.15
            )
            logger.info(f"[{stream_id}] ObjectTracker initialized")

            # Per-stream lock for motion state access (T013, FR-024, FR-031)
            motion_lock = threading.Lock()

            # Pre-register (prevents race condition in get_frame)
            self.active_processes[stream_id] = {
                "process": None,
                "buffer": bytearray(),
                "detection_config": stream.get("detection", {}),
                "stream_dimensions": None,  # Will be populated from FFprobe
                "motion_detector": motion_detector,  # T013
                "motion_lock": motion_lock,  # T013
                "last_motion_timestamp": None,  # For 300-second no-motion fallback (T016)
                "object_tracker": object_tracker,  # T039
                "frame_count": 0,  # T039: Frame counter for tracking
                "motion_error_count": 0,  # Track consecutive motion detection errors
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

            # Get stream dimensions (ALWAYS needed for detection)
            try:
                logger.debug(f"[{stream_id}] Probing stream dimensions for detection...")
                dimensions = await self._probe_stream_dimensions(url)
                self.active_processes[stream_id]["stream_dimensions"] = dimensions
                logger.info(f"[{stream_id}] Stream dimensions for detection: {dimensions[0]}x{dimensions[1]}")
            except Exception as e:
                logger.warning(f"[{stream_id}] Failed to probe dimensions: {e}")
                logger.warning(f"[{stream_id}] Detection may not work correctly without dimensions")

            # Start stderr monitor
            asyncio.create_task(self._monitor_ffmpeg_stderr(stream_id, process))

            # Start continuous frame processor (fixes B1, B2)
            asyncio.create_task(self._continuous_frame_processor(stream_id))
            logger.info(f"[{stream_id}] Started continuous frame processor background task")

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

            # Clean up motion detector and object tracker (T018, T043)
            motion_detector = proc_data.get("motion_detector")
            if motion_detector:
                motion_detector.reset()
                logger.debug(f"[{stream_id}] MotionDetector reset and cleaned up")

            object_tracker = proc_data.get("object_tracker")
            if object_tracker:
                object_tracker.reset()
                logger.debug(f"[{stream_id}] ObjectTracker reset and cleaned up")

            # Terminate FFmpeg process
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

    async def get_frame_for_mjpeg(self, stream_id: str) -> tuple[bool, bytes] | None:
        """Get latest processed frame and encode to JPEG for MJPEG streaming.

        This method retrieves the latest frame processed by the continuous
        frame processor background task. JPEG encoding only happens when
        viewers request frames (B7 optimization).

        Args:
            stream_id: Stream UUID

        Returns:
            (success, jpeg_bytes) if available, None if stream ended
        """
        if stream_id not in self.active_processes:
            logger.warning(f"Frame request for inactive stream: {stream_id}")
            return None

        proc_data = self.active_processes[stream_id]
        latest_frame = proc_data.get("latest_frame")

        if latest_frame is None:
            # No frame available yet (or no viewers so no rendering)
            return (False, b'')

        # JPEG encode only when viewer requests it (B7 optimization)
        import cv2
        try:
            _, jpeg_bytes = cv2.imencode('.jpg', latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return (True, jpeg_bytes.tobytes())
        except Exception as e:
            logger.error(f"[{stream_id}] JPEG encoding error: {e}", exc_info=True)
            return (False, b'')

    async def get_frame(self, stream_id: str) -> tuple[bool, bytes] | None:
        """Get next frame from FFmpeg stdout with YOLO object detection.

        Reads raw BGR24 frames from FFmpeg, runs YOLO inference, renders bounding boxes
        with labels and confidence scores, and encodes to JPEG for streaming.

        Detection is ALWAYS enabled - this is the core purpose of the application.

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
            # DETECTION MODE: Always process with YOLO detection
            # This is the core purpose of the application
            return await self._get_frame_with_detection(stream_id, proc_data)

        except Exception as e:
            logger.error(f"Frame read error for {stream_id}: {e}", exc_info=True)
            return None

    async def _get_mjpeg_frame(self, stream_id: str, proc_data: dict) -> tuple[bool, bytes] | None:
        """Extract MJPEG frame from buffer (original logic)."""
        process = proc_data["process"]
        buffer = proc_data["buffer"]

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

    async def _get_frame_with_detection(self, stream_id: str, proc_data: dict) -> tuple[bool, bytes] | None:
        """Extract raw BGR24 frame, run detection, render, encode to JPEG."""
        import numpy as np
        import cv2
        import time
        from ..api.detection import get_onnx_session, get_yolo_config_singleton
        from ..services.detection import (
            preprocess_frame, run_inference, parse_detections,
            filter_detections, render_bounding_boxes
        )

        logger.debug(f"[{stream_id}] Starting detection frame processing")
        pipeline_start = time.perf_counter()

        process = proc_data["process"]
        buffer = proc_data["buffer"]
        dimensions = proc_data.get("stream_dimensions")

        if not dimensions:
            logger.error(f"[{stream_id}] Stream dimensions unknown for detection")
            return (False, b'')

        width, height = dimensions
        frame_size = width * height * 3  # BGR = 3 bytes per pixel

        # Sanity check: Prevent buffer overflow from malformed dimensions
        # 4K = 3840x2160x3 = 24,883,200 bytes (~25MB), so cap at 30MB
        MAX_FRAME_SIZE = 30 * 1024 * 1024  # 30MB
        if frame_size > MAX_FRAME_SIZE:
            logger.error(
                f"[{stream_id}] Frame size {frame_size} bytes exceeds maximum {MAX_FRAME_SIZE} bytes. "
                f"Dimensions {width}x{height} may be incorrect. Stopping stream."
            )
            return (False, b'')

        logger.debug(f"[{stream_id}] Reading raw BGR24 frame: {width}x{height} = {frame_size} bytes")

        # Read raw frame bytes
        read_start = time.perf_counter()
        while len(buffer) < frame_size:
            # Additional safety: check buffer doesn't exceed expected size during accumulation
            if len(buffer) > MAX_FRAME_SIZE:
                logger.error(
                    f"[{stream_id}] Buffer overflow during frame read: {len(buffer)} bytes exceeds {MAX_FRAME_SIZE}. "
                    "FFmpeg may be producing malformed output."
                )
                return (False, b'')

            try:
                chunk = await asyncio.wait_for(
                    process.stdout.read(frame_size - len(buffer)),
                    timeout=FRAME_READ_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.warning(f"[{stream_id}] Timeout waiting for raw frame data (buffer: {len(buffer)}/{frame_size} bytes)")
                return (False, b'')

            if not chunk:
                logger.error(f"[{stream_id}] FFmpeg stdout closed during detection frame read")
                return None

            buffer.extend(chunk)

        read_time_ms = (time.perf_counter() - read_start) * 1000
        logger.debug(f"[{stream_id}] Frame read complete: {read_time_ms:.1f}ms")

        # Extract frame bytes
        frame_bytes = bytes(buffer[:frame_size])
        del buffer[:frame_size]

        # Convert to NumPy array
        frame_bgr = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((height, width, 3))
        logger.debug(f"[{stream_id}] Converted to NumPy array: shape={frame_bgr.shape}")

        # Run detection pipeline
        try:
            onnx_session = get_onnx_session()
            if onnx_session is None:
                logger.warning(f"[{stream_id}] ONNX session not available, skipping detection")
                # Encode without detection
                encode_start = time.perf_counter()
                _, jpeg_bytes = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
                encode_time_ms = (time.perf_counter() - encode_start) * 1000
                logger.debug(f"[{stream_id}] Encoded frame without detection: {encode_time_ms:.1f}ms")
                return (True, jpeg_bytes.tobytes())

            detection_config = proc_data.get("detection_config", {})
            enabled_labels = detection_config.get("enabled_labels", ["person"])
            min_confidence = detection_config.get("min_confidence", 0.8)
            logger.debug(f"[{stream_id}] Detection config: labels={enabled_labels}, min_conf={min_confidence}")

            # Get YOLO model image size (must match ONNX model input dimensions)
            yolo_config = get_yolo_config_singleton()
            if yolo_config is None:
                logger.error(f"[{stream_id}] YOLO config not available")
                # Fallback: encode without detection
                _, jpeg_bytes = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
                return (True, jpeg_bytes.tobytes())

            target_size = yolo_config.image_size
            logger.debug(f"[{stream_id}] Using YOLO image size: {target_size}x{target_size}")

            # Preprocess
            preprocess_start = time.perf_counter()
            preprocessed, scale, padding = preprocess_frame(frame_bgr, target_size=target_size)
            preprocess_time_ms = (time.perf_counter() - preprocess_start) * 1000
            logger.debug(f"[{stream_id}] Preprocessing: {preprocess_time_ms:.1f}ms")

            # Inference
            inference_start = time.perf_counter()
            outputs = run_inference(onnx_session, preprocessed)
            inference_time_ms = (time.perf_counter() - inference_start) * 1000
            logger.debug(f"[{stream_id}] Inference: {inference_time_ms:.1f}ms")

            # Parse detections
            parse_start = time.perf_counter()
            detections = parse_detections(outputs, scale, padding, (height, width))
            parse_time_ms = (time.perf_counter() - parse_start) * 1000
            logger.debug(f"[{stream_id}] Parsing: {parse_time_ms:.1f}ms, detections={len(detections)}")

            # Filter
            filter_start = time.perf_counter()
            filtered_detections = filter_detections(detections, enabled_labels, min_confidence)
            filter_time_ms = (time.perf_counter() - filter_start) * 1000
            logger.debug(f"[{stream_id}] Filtering: {filter_time_ms:.1f}ms, filtered={len(filtered_detections)}")

            # Render bounding boxes
            render_start = time.perf_counter()
            render_bounding_boxes(frame_bgr, filtered_detections)
            render_time_ms = (time.perf_counter() - render_start) * 1000
            logger.debug(f"[{stream_id}] Rendering: {render_time_ms:.1f}ms")

            # Encode to JPEG
            encode_start = time.perf_counter()
            _, jpeg_bytes = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
            encode_time_ms = (time.perf_counter() - encode_start) * 1000
            logger.debug(f"[{stream_id}] Encoding: {encode_time_ms:.1f}ms")

            total_time_ms = (time.perf_counter() - pipeline_start) * 1000
            logger.info(f"[{stream_id}] Detection pipeline complete: {total_time_ms:.1f}ms total, {len(filtered_detections)} detections")

            return (True, jpeg_bytes.tobytes())

        except Exception as e:
            logger.error(f"[{stream_id}] Detection pipeline error: {e}", exc_info=True)
            # Fallback: encode frame without detection
            _, jpeg_bytes = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return (True, jpeg_bytes.tobytes())
    
    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _probe_stream_dimensions(self, rtsp_url: str) -> tuple[int, int]:
        """Probe RTSP stream to get video dimensions using ffprobe.

        Args:
            rtsp_url: RTSP URL to probe

        Returns:
            Tuple of (width, height)
        """
        import json

        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "v:0",
            rtsp_url
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)

        if process.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

        data = json.loads(stdout.decode())
        stream_info = data.get("streams", [{}])[0]
        width = stream_info.get("width")
        height = stream_info.get("height")

        if not width or not height:
            raise ValueError("Could not determine stream dimensions")

        return (int(width), int(height))

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
    
    def _get_default_ffmpeg_params(self, hw_accel_enabled: bool = True) -> list[str]:
        """Get default FFmpeg parameters for GPU backend.
        
        Args:
            hw_accel_enabled: Always True (kept for compatibility)
            
        Returns:
            List of FFmpeg parameter strings with GPU acceleration
        """
        # Use centralized config module
        return get_default_ffmpeg_params(self.gpu_backend)

    def get_motion_metrics(self, stream_id: str):
        """Get current motion detection metrics for stream.

        Args:
            stream_id: Stream UUID

        Returns:
            MotionDetectionMetrics instance or None if not available
        """
        if stream_id not in self.active_processes:
            logger.warning(f"Motion metrics request for inactive stream: {stream_id}")
            return None

        proc_data = self.active_processes[stream_id]

        # Return last metrics (set by _continuous_frame_processor)
        return proc_data.get("motion_metrics")

    def get_tracked_objects(self, stream_id: str, state_filter: str | None = None):
        """Get currently tracked objects for stream.

        Args:
            stream_id: Stream UUID
            state_filter: Optional ObjectState filter (tentative, active, stationary, lost)

        Returns:
            List of TrackedObject instances or None if not available

        Raises:
            ValueError: Invalid state filter
        """
        from app.models.motion import ObjectState

        if stream_id not in self.active_processes:
            logger.warning(f"Tracked objects request for inactive stream: {stream_id}")
            return None

        proc_data = self.active_processes[stream_id]
        object_tracker = proc_data.get("object_tracker")

        if not object_tracker:
            logger.warning(f"Object tracker not initialized for stream: {stream_id}")
            return None

        # Get all tracks
        tracks = object_tracker.tracks

        # Apply state filter if requested
        if state_filter:
            try:
                # Validate state filter
                filter_state = ObjectState(state_filter.lower())
                tracks = [t for t in tracks if t.state == filter_state]
                logger.debug(f"Filtered tracks by state={filter_state}: {len(tracks)} tracks")
            except ValueError:
                raise ValueError(f"Invalid state filter: {state_filter}. Must be one of: tentative, active, stationary, lost")

        return tracks

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