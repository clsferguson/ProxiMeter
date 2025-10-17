"""Prometheus metrics for the application."""
from __future__ import annotations

from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST


# Define metrics
counter_value_gauge = Gauge(
    "hello_counter_value",
    "Current value of the hello counter"
)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
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
