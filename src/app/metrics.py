"""Prometheus metrics for observability.

Provides metrics for:
- HTTP requests (count, latency, in-progress)
- Stream management (CRUD operations, active count)
- Zone management (CRUD operations)
- MJPEG playback (sessions, frames, FPS)
- System health (status checks)

Future metrics (defined but not yet used):
- Stream processing (FPS, bitrate, latency)
- FFmpeg processes (CPU, memory, restarts)
- GPU metrics (utilization, memory, temperature)
- Detection counts per zone

Logging Strategy:
    INFO  - Module initialization
    DEBUG - Helper function calls (disabled by default)
    ERROR - Metric generation failures
"""
from __future__ import annotations

import logging
from typing import Final

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY
)

logger = logging.getLogger(__name__)

# ============================================================================
# Application Info
# ============================================================================

app_info = Info("proximeter_app", "Application information")
app_info.info({
    "version": "1.0.0",
    "name": "ProxiMeter",
    "description": "RTSP Stream Management with Zone Detection"
})

# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests in progress",
    ["method", "endpoint"]
)

# ============================================================================
# Stream Management Metrics
# ============================================================================

streams_total = Gauge("streams_total", "Total configured streams")
streams_active = Gauge("streams_active", "Currently running streams")

streams_created_total = Counter("streams_created_total", "Streams created")
streams_deleted_total = Counter("streams_deleted_total", "Streams deleted")
streams_updated_total = Counter("streams_updated_total", "Stream updates")
streams_reordered_total = Counter("streams_reordered_total", "Reorder operations")

streams_start_total = Counter(
    "streams_start_total",
    "Stream start attempts",
    ["status"]  # success, failure
)
streams_stop_total = Counter("streams_stop_total", "Stream stop operations")

# ============================================================================
# Zone Detection Metrics
# ============================================================================

zones_total = Gauge("zones_total", "Total configured zones")
zones_created_total = Counter("zones_created_total", "Zones created")
zones_deleted_total = Counter("zones_deleted_total", "Zones deleted")

detections_total = Counter(
    "detections_total",
    "Object detections (future)",
    ["stream_id", "zone_id"]
)

# ============================================================================
# MJPEG Playback Metrics
# ============================================================================

playback_sessions_active = Gauge("playback_sessions_active", "Active MJPEG sessions")
playback_sessions_total = Counter("playback_sessions_total", "MJPEG sessions started", ["stream_id"])
playback_frames_total = Counter("playback_frames_total", "MJPEG frames served", ["stream_id"])

playback_frame_size_bytes = Histogram(
    "playback_frame_size_bytes",
    "MJPEG frame size",
    ["stream_id"],
    buckets=(1024, 5120, 10240, 25600, 51200, 102400, 204800, 512000, 1048576)
)

playback_fps_current = Gauge("playback_fps_current", "Current playback FPS", ["stream_id"])

# ============================================================================
# Stream Processing Metrics (Future)
# ============================================================================

stream_fps = Gauge("stream_fps", "Stream FPS", ["stream_id"])
stream_bitrate_kbps = Gauge("stream_bitrate_kbps", "Stream bitrate", ["stream_id"])
stream_latency_seconds = Gauge("stream_latency_seconds", "Processing latency", ["stream_id"])

stream_frames_dropped_total = Counter(
    "stream_frames_dropped_total",
    "Dropped frames",
    ["stream_id", "reason"]
)

stream_errors_total = Counter(
    "stream_errors_total",
    "Stream errors",
    ["stream_id", "error_type"]
)

# ============================================================================
# FFmpeg Process Metrics (Future)
# ============================================================================

ffmpeg_processes_active = Gauge("ffmpeg_processes_active", "Active FFmpeg processes")
ffmpeg_process_restarts_total = Counter("ffmpeg_process_restarts_total", "FFmpeg restarts", ["stream_id", "reason"])
ffmpeg_process_cpu_percent = Gauge("ffmpeg_process_cpu_percent", "FFmpeg CPU %", ["stream_id"])
ffmpeg_process_memory_bytes = Gauge("ffmpeg_process_memory_bytes", "FFmpeg memory", ["stream_id"])

# ============================================================================
# GPU Metrics (Future)
# ============================================================================

gpu_utilization_percent = Gauge("gpu_utilization_percent", "GPU utilization", ["gpu_id", "backend"])
gpu_memory_used_bytes = Gauge("gpu_memory_used_bytes", "GPU memory used", ["gpu_id", "backend"])
gpu_memory_total_bytes = Gauge("gpu_memory_total_bytes", "GPU memory total", ["gpu_id", "backend"])
gpu_temperature_celsius = Gauge("gpu_temperature_celsius", "GPU temperature", ["gpu_id", "backend"])

# ============================================================================
# Motion Detection Metrics (Feature 006, T067)
# ============================================================================

motion_detection_duration_seconds = Histogram(
    "motion_detection_duration_seconds",
    "Motion detection processing time per frame",
    ["stream_id"],
    buckets=(0.001, 0.005, 0.010, 0.015, 0.020, 0.025, 0.050, 0.100, 0.200)
)

yolo_inference_duration_seconds = Histogram(
    "yolo_inference_duration_seconds",
    "YOLO inference processing time per frame",
    ["stream_id"],
    buckets=(0.01, 0.025, 0.050, 0.100, 0.150, 0.200, 0.250, 0.500, 1.0)
)

tracking_duration_seconds = Histogram(
    "tracking_duration_seconds",
    "Object tracking processing time per frame",
    ["stream_id"],
    buckets=(0.001, 0.002, 0.005, 0.010, 0.015, 0.020, 0.025, 0.050)
)

tracked_objects_total = Gauge(
    "tracked_objects_total",
    "Currently tracked objects by state",
    ["stream_id", "state"]
)

motion_regions_detected = Gauge(
    "motion_regions_detected",
    "Number of motion regions detected in current frame",
    ["stream_id"]
)

# ============================================================================
# System Health Metrics
# ============================================================================

health_status = Gauge("health_status", "Health status (1=healthy, 0.5=degraded, 0=unhealthy)")

health_checks_total = Counter(
    "health_checks_total",
    "Health check requests",
    ["check_type", "status"]
)

# ============================================================================
# Metrics Export
# ============================================================================

def get_metrics() -> tuple[bytes, int, dict[str, str]]:
    """Generate Prometheus metrics in text format.
    
    Returns:
        (body, status_code, headers) for FastAPI Response
    """
    try:
        metrics = generate_latest(REGISTRY)
        return (metrics, 200, {"Content-Type": CONTENT_TYPE_LATEST})
    except Exception as e:
        logger.error(f"Metrics generation failed: {e}", exc_info=True)
        return (b"# Error\n", 500, {"Content-Type": "text/plain"})


# ============================================================================
# Helper Functions
# ============================================================================

def track_http_request(method: str, endpoint: str, status_code: int) -> None:
    """Track HTTP request in metrics."""
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=str(status_code)
    ).inc()


def update_stream_count(total: int, active: int) -> None:
    """Update stream count gauges."""
    streams_total.set(total)
    streams_active.set(active)


def update_health_status(status: str) -> None:
    """Update health status gauge.
    
    Args:
        status: "healthy" (1.0), "degraded" (0.5), "unhealthy" (0.0)
    """
    status_map = {"healthy": 1.0, "degraded": 0.5, "unhealthy": 0.0}
    health_status.set(status_map.get(status, 0.0))


logger.info("Prometheus metrics initialized")