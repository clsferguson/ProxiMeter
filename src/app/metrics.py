"""Prometheus metrics for the application."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST


# Legacy counter metric (to be removed in US3)
counter_value_gauge = Gauge(
    "hello_counter_value",
    "Current value of the hello counter"
)

# HTTP request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

# Stream-related metrics (T039)
streams_created_total = Counter(
    "streams_created_total",
    "Total number of streams created"
)

streams_deleted_total = Counter(
    "streams_deleted_total",
    "Total number of streams deleted"
)

streams_reordered_total = Counter(
    "streams_reordered_total",
    "Total number of stream reorder operations"
)

active_playback_sessions = Gauge(
    "active_playback_sessions",
    "Number of active MJPEG playback sessions"
)

playback_frames_total = Counter(
    "playback_frames_total",
    "Total number of MJPEG frames served",
    ["stream_id"]
)

playback_fps_gauge = Gauge(
    "playback_fps_current",
    "Current playback FPS for active streams",
    ["stream_id"]
)


def get_metrics() -> tuple[bytes, int, dict[str, str]]:
    """Generate Prometheus metrics in text format.
    
    Returns:
        Tuple of (body, status_code, headers)
    """
    metrics_output = generate_latest()
    return (
        metrics_output,
        200,
        {"Content-Type": CONTENT_TYPE_LATEST}
    )
