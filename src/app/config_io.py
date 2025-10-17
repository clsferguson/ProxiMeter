from __future__ import annotations

import io
import os
import tempfile
import threading
from typing import Any, Tuple

import yaml


CONFIG_DIR = os.path.join(os.getcwd(), "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yml")
COUNTER_KEY = "counter"
STREAMS_KEY = "streams"
COUNTER_MIN = 0
COUNTER_MAX = 2_147_483_647

# CI_DRY_RUN mode: use in-memory storage instead of disk
_dry_run_mode = os.environ.get("CI_DRY_RUN", "").lower() in ("true", "1", "yes")
_in_memory_counter = COUNTER_MIN
_in_memory_streams: list[dict[str, Any]] = []
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


def load_streams() -> list[dict[str, Any]]:
    """Load streams list from YAML or in-memory (if CI_DRY_RUN=true).
    
    Returns a list of stream dictionaries. If the file is missing or malformed,
    returns an empty list and initializes the file.
    """
    global _in_memory_streams
    
    # In dry-run mode, use in-memory storage
    if _dry_run_mode:
        with _lock:
            return _in_memory_streams.copy()
    
    _ensure_config_dir()
    if not os.path.exists(CONFIG_PATH):
        # Initialize file with empty streams list
        save_streams([])
        return []
    
    try:
        with io.open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        streams = data.get(STREAMS_KEY, [])
        if not isinstance(streams, list):
            streams = []
        return streams
    except Exception:
        # On error, return empty list and reinitialize
        save_streams([])
        return []


def save_streams(streams: list[dict[str, Any]]) -> None:
    """Persist streams list to YAML with atomic write or in-memory (if CI_DRY_RUN=true).
    
    Uses atomic write pattern: write to temp file, then rename to target.
    Normalizes order field to be contiguous starting from 0.
    
    Args:
        streams: List of stream dictionaries to persist
    """
    global _in_memory_streams
    
    # Normalize order field to be contiguous
    normalized_streams = []
    for idx, stream in enumerate(streams):
        stream_copy = stream.copy()
        stream_copy["order"] = idx
        normalized_streams.append(stream_copy)
    
    # In dry-run mode, update in-memory storage only
    if _dry_run_mode:
        with _lock:
            _in_memory_streams = normalized_streams.copy()
        return
    
    _ensure_config_dir()
    
    # Atomic write: write to temp file, then rename
    with _lock:
        # Create temp file in same directory as target for atomic rename
        fd, temp_path = tempfile.mkstemp(
            dir=CONFIG_DIR,
            prefix=".config_",
            suffix=".yml.tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.safe_dump({STREAMS_KEY: normalized_streams}, f, sort_keys=True)
            
            # Atomic rename (on POSIX) or best-effort on Windows
            if os.name == "nt":
                # Windows: remove target first if exists
                if os.path.exists(CONFIG_PATH):
                    os.remove(CONFIG_PATH)
            os.rename(temp_path, CONFIG_PATH)
        except Exception:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
