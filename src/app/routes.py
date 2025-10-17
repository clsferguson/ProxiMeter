from __future__ import annotations

from flask import Blueprint, Flask, jsonify, render_template, request

from .config_io import load_counter, save_counter, COUNTER_MAX
from .metrics import counter_value_gauge, http_requests_total, get_metrics


bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    value, warning = load_counter()
    counter_value_gauge.set(value)
    return render_template("index.html", counter=value, warning=warning)


@bp.get("/api/counter")
def get_counter():
    value, _ = load_counter()
    counter_value_gauge.set(value)
    return jsonify({"counter": value})


@bp.post("/api/counter")
def increment_counter():
    value, _ = load_counter()
    if value < COUNTER_MAX:
        value += 1
        save_counter(value)
    counter_value_gauge.set(value)
    return jsonify({"counter": value})


@bp.get("/health")
def health():
    return ("ok", 200, {"Content-Type": "text/plain; charset=utf-8"})


@bp.get("/metrics")
def metrics():
    return get_metrics()


def register_blueprint(app: Flask) -> None:
    app.register_blueprint(bp)
    
    # Add after_request handler to track HTTP requests
    @app.after_request
    def track_requests(response):
        http_requests_total.labels(
            method=request.method,
            endpoint=request.endpoint or "unknown",
            status=response.status_code
        ).inc()
        return response
