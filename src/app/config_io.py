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

# CI_DRY_RUN mode: use in-memory counter instead of disk
_dry_run_mode = os.environ.get("CI_DRY_RUN", "").lower() in ("true", "1", "yes")
_in_memory_counter = COUNTER_MIN
_lock = threading.Lock()


def _ensure_config_dir() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_counter() -> Tuple[int, str | None]:
    """Load the counter from YAML or in-memory (if CI_DRY_RUN=true).

    Returns a tuple of (value, warning_message).
    If the file is missing or malformed, returns 0 and a warning.
    """
    global _in_memory_counter
    
    # In dry-run mode, use in-memory counter
    if _dry_run_mode:
        with _lock:
            return _in_memory_counter, None
    
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
    """Persist the counter value to YAML or in-memory (if CI_DRY_RUN=true), clamped to allowed range."""
    global _in_memory_counter
    
    clamped = max(COUNTER_MIN, min(COUNTER_MAX, int(value)))
    
    # In dry-run mode, update in-memory counter only
    if _dry_run_mode:
        with _lock:
            _in_memory_counter = clamped
        return
    
    _ensure_config_dir()
    with _lock:
        with io.open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump({COUNTER_KEY: clamped}, f, sort_keys=True)
