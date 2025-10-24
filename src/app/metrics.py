"""Prometheus metrics for application observability."""
from __future__ import annotations

from typing import Final
import logging

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

app_info = Info(
    "proximeter_app",
    "ProxiMeter application information"
)

# Set application metadata
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
    "Total HTTP requests by method, endpoint, and status code",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"]
)


# ============================================================================
# Stream Management Metrics
# ============================================================================

streams_total = Gauge(
    "streams_total",
    "Total number of configured streams"
)

streams_active = Gauge(
    "streams_active",
    "Number of currently running streams"
)

streams_created_total = Counter(
    "streams_created_total",
    "Total number of streams created since startup"
)

streams_deleted_total = Counter(
    "streams_deleted_total",
    "Total number of streams deleted since startup"
)

streams_updated_total = Counter(
    "streams_updated_total",
    "Total number of stream updates since startup"
)

streams_reordered_total = Counter(
    "streams_reordered_total",
    "Total number of stream reorder operations since startup"
)

streams_start_total = Counter(
    "streams_start_total",
    "Total number of stream start attempts",
    ["status"]  # success, failure
)

streams_stop_total = Counter(
    "streams_stop_total",
    "Total number of stream stop operations"
)


# ============================================================================
# Zone Detection Metrics
# ============================================================================

zones_total = Gauge(
    "zones_total",
    "Total number of configured detection zones"
)

zones_created_total = Counter(
    "zones_created_total",
    "Total number of zones created since startup"
)

zones_deleted_total = Counter(
    "zones_deleted_total",
    "Total number of zones deleted since startup"
)

detections_total = Counter(
    "detections_total",
    "Total number of object detections",
    ["stream_id", "zone_id"]
)


# ============================================================================
# MJPEG Playback Metrics
# ============================================================================

playback_sessions_active = Gauge(
    "playback_sessions_active",
    "Number of active MJPEG playback sessions"
)

playback_sessions_total = Counter(
    "playback_sessions_total",
    "Total number of MJPEG playback sessions started",
    ["stream_id"]
)

playback_frames_total = Counter(
    "playback_frames_total",
    "Total number of MJPEG frames served",
    ["stream_id"]
)

playback_frame_size_bytes = Histogram(
    "playback_frame_size_bytes",
    "MJPEG frame size in bytes",
    ["stream_id"],
    buckets=(1024, 5120, 10240, 25600, 51200, 102400, 204800, 512000, 1048576)
)

playback_fps_current = Gauge(
    "playback_fps_current",
    "Current playback FPS for active streams",
    ["stream_id"]
)


# ============================================================================
# Stream Processing Metrics
# ============================================================================

stream_fps = Gauge(
    "stream_fps",
    "Current frames per second per stream",
    ["stream_id"]
)

stream_bitrate_kbps = Gauge(
    "stream_bitrate_kbps",
    "Current bitrate in kbps per stream",
    ["stream_id"]
)

stream_latency_seconds = Gauge(
    "stream_latency_seconds",
    "Current processing latency in seconds per stream",
    ["stream_id"]
)

stream_frames_dropped_total = Counter(
    "stream_frames_dropped_total",
    "Total number of dropped frames per stream",
    ["stream_id", "reason"]  # buffer_full, decode_error, timeout
)

stream_errors_total = Counter(
    "stream_errors_total",
    "Total number of stream processing errors",
    ["stream_id", "error_type"]
)


# ============================================================================
# FFmpeg Process Metrics
# ============================================================================

ffmpeg_processes_active = Gauge(
    "ffmpeg_processes_active",
    "Number of active FFmpeg processes"
)

ffmpeg_process_restarts_total = Counter(
    "ffmpeg_process_restarts_total",
    "Total number of FFmpeg process restarts",
    ["stream_id", "reason"]
)

ffmpeg_process_cpu_percent = Gauge(
    "ffmpeg_process_cpu_percent",
    "FFmpeg process CPU usage percentage",
    ["stream_id"]
)

ffmpeg_process_memory_bytes = Gauge(
    "ffmpeg_process_memory_bytes",
    "FFmpeg process memory usage in bytes",
    ["stream_id"]
)


# ============================================================================
# GPU Metrics
# ============================================================================

gpu_utilization_percent = Gauge(
    "gpu_utilization_percent",
    "GPU utilization percentage",
    ["gpu_id", "backend"]  # backend: nvidia, amd, intel
)

gpu_memory_used_bytes = Gauge(
    "gpu_memory_used_bytes",
    "GPU memory usage in bytes",
    ["gpu_id", "backend"]
)

gpu_memory_total_bytes = Gauge(
    "gpu_memory_total_bytes",
    "Total GPU memory in bytes",
    ["gpu_id", "backend"]
)

gpu_temperature_celsius = Gauge(
    "gpu_temperature_celsius",
    "GPU temperature in Celsius",
    ["gpu_id", "backend"]
)


# ============================================================================
# System Health Metrics
# ============================================================================

health_status = Gauge(
    "health_status",
    "Overall health status (1=healthy, 0.5=degraded, 0=unhealthy)"
)

health_checks_total = Counter(
    "health_checks_total",
    "Total number of health check requests",
    ["check_type", "status"]  # check_type: full, liveness, readiness, startup
)


# ============================================================================
# Metrics Export
# ============================================================================

def get_metrics() -> tuple[bytes, int, dict[str, str]]:
    """Generate Prometheus metrics in text format.
    
    Returns:
        Tuple of (response_body, status_code, headers) for FastAPI Response
        
    Example:
        >>> body, status, headers = get_metrics()
        >>> return Response(content=body, status_code=status, headers=headers)
    """
    try:
        metrics_output = generate_latest(REGISTRY)
        return (
            metrics_output,
            200,
            {"Content-Type": CONTENT_TYPE_LATEST}
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return (
            b"# Error generating metrics\n",
            500,
            {"Content-Type": "text/plain"}
        )


def reset_metrics() -> None:
    """Reset all metrics (useful for testing).
    
    Warning: This clears all metric values. Use with caution.
    Only intended for development/testing environments.
    """
    logger.warning("Resetting all Prometheus metrics")
    
    # Clear all collector data
    for collector in list(REGISTRY._collector_to_names.keys()):
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass


# ============================================================================
# Metric Helper Functions
# ============================================================================

def track_http_request(method: str, endpoint: str, status_code: int) -> None:
    """Track an HTTP request.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        status_code: HTTP status code
    """
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=str(status_code)
    ).inc()


def update_stream_count(total: int, active: int) -> None:
    """Update stream count metrics.
    
    Args:
        total: Total number of streams
        active: Number of active streams
    """
    streams_total.set(total)
    streams_active.set(active)


def update_health_status(status: str) -> None:
    """Update health status metric.
    
    Args:
        status: Health status (healthy, degraded, unhealthy)
    """
    status_map = {
        "healthy": 1.0,
        "degraded": 0.5,
        "unhealthy": 0.0
    }
    health_status.set(status_map.get(status, 0.0))
