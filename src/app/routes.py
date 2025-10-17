from __future__ import annotations

from flask import Blueprint, Flask, jsonify, render_template

from .config_io import load_counter, save_counter, COUNTER_MAX


bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    value, warning = load_counter()
    return render_template("index.html", counter=value, warning=warning)


@bp.get("/api/counter")
def get_counter():
    value, _ = load_counter()
    return jsonify({"counter": value})


@bp.post("/api/counter")
def increment_counter():
    value, _ = load_counter()
    if value < COUNTER_MAX:
        value += 1
        save_counter(value)
    return jsonify({"counter": value})


@bp.get("/health")
def health():
    return ("ok", 200, {"Content-Type": "text/plain; charset=utf-8"})


def register_blueprint(app: Flask) -> None:
    app.register_blueprint(bp)
