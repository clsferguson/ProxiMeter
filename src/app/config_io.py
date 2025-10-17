from __future__ import annotations

import io
import os
import threading
from typing import Tuple

import yaml


CONFIG_DIR = os.path.join(os.getcwd(), "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yml")
COUNTER_KEY = "counter"
COUNTER_MIN = 0
COUNTER_MAX = 2_147_483_647

_lock = threading.Lock()


def _ensure_config_dir() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_counter() -> Tuple[int, str | None]:
    """Load the counter from YAML.

    Returns a tuple of (value, warning_message).
    If the file is missing or malformed, returns 0 and a warning.
    """
    _ensure_config_dir()
    if not os.path.exists(CONFIG_PATH):
        # Initialize file with default
        save_counter(COUNTER_MIN)
        return COUNTER_MIN, None

    try:
        with io.open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        value = int(data.get(COUNTER_KEY, COUNTER_MIN))
    except Exception:
        return COUNTER_MIN, "Configuration malformed; using default 0."

    if value < COUNTER_MIN:
        value = COUNTER_MIN
    if value > COUNTER_MAX:
        value = COUNTER_MAX
    return value, None


def save_counter(value: int) -> None:
    """Persist the counter value to YAML, clamped to allowed range."""
    _ensure_config_dir()
    clamped = max(COUNTER_MIN, min(COUNTER_MAX, int(value)))
    with _lock:
        with io.open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump({COUNTER_KEY: clamped}, f, sort_keys=True)
