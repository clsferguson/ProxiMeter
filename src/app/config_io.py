"""Thread-safe YAML configuration with atomic writes.

Persistent storage for ProxiMeter using YAML with corruption protection.

Features:
    - Thread-safe with RLock (prevents race conditions)
    - Atomic writes (temp file + rename)
    - Auto-recovery from corruption
    - In-memory mode for CI/testing (CI_DRY_RUN=true)
    - Stream order normalization

Storage Modes:
    Production: /app/config/config.yml
    CI/Testing: In-memory dict (no disk I/O)

Thread Safety:
    RLock prevents concurrent read/write races and partial reads.

Atomic Writes:
    1. Write to temp file
    2. Atomic rename (POSIX) or best-effort (Windows)
    3. Never corrupts config even if process crashes

Logging Strategy:
    DEBUG - File operations, normalization
    INFO  - Init, mode selection
    WARN  - Invalid formats, recovery, invalid GPU
    ERROR - YAML parsing, I/O failures
"""
from __future__ import annotations

import io
import logging
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final, Iterator

import yaml

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

CONFIG_DIR: Final[Path] = Path(os.getenv("CONFIG_DIR", "/app/config"))
CONFIG_PATH: Final[Path] = CONFIG_DIR / "config.yml"
STREAMS_KEY: Final[str] = "streams"

# CI/Testing: in-memory storage
_DRY_RUN_MODE: Final[bool] = os.getenv("CI_DRY_RUN", "").lower() in ("true", "1", "yes")

# Thread-safe storage
_in_memory_config: dict[str, Any] = {STREAMS_KEY: []}
_config_lock = threading.RLock()

# ============================================================================
# Initialization
# ============================================================================

def _ensure_config_dir() -> None:
    """Ensure config directory exists."""
    if not _DRY_RUN_MODE:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create config dir: {e}", exc_info=True)
            raise


def _initialize_config_file() -> None:
    """Initialize empty config file."""
    if not _DRY_RUN_MODE:
        logger.info(f"Initializing config: {CONFIG_PATH}")
        save_streams({STREAMS_KEY: []})


# ============================================================================
# Atomic Read-Modify-Write Context Manager
# ============================================================================

@contextmanager
def atomic_config_update() -> Iterator[dict[str, Any]]:
    """Context manager for atomic read-modify-write operations.

    Usage:
        with atomic_config_update() as config:
            # Modify config
            config["streams"].append(new_stream)
            # Changes are automatically saved on context exit

    This prevents race conditions by holding the lock during the entire
    read-modify-write sequence.
    """
    with _config_lock:
        # Load config while holding lock
        config = load_streams()

        # Yield to caller for modifications
        yield config

        # Save config while still holding lock
        save_streams(config)


# ============================================================================
# Configuration Loading
# ============================================================================

def load_streams() -> dict[str, Any]:
    """Load configuration with auto-recovery.
    
    Returns:
        Config dict with 'streams' key containing stream list
    """
    # Dry-run: in-memory
    if _DRY_RUN_MODE:
        with _config_lock:
            return _in_memory_config.copy()
    
    _ensure_config_dir()
    
    # Initialize if missing
    if not CONFIG_PATH.exists():
        _initialize_config_file()
        return {STREAMS_KEY: []}
    
    # Load with recovery
    with _config_lock:
        try:
            with io.open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            # Validate structure
            if not isinstance(data, dict):
                logger.warning(f"Invalid config format (expected dict), reinitializing")
                _initialize_config_file()
                return {STREAMS_KEY: []}
            
            # Ensure streams list exists
            if STREAMS_KEY not in data:
                data[STREAMS_KEY] = []
            elif not isinstance(data[STREAMS_KEY], list):
                logger.warning(f"Invalid streams format (expected list), reinitializing")
                data[STREAMS_KEY] = []
            
            logger.debug(f"Loaded {len(data[STREAMS_KEY])} stream(s)")
            return data
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}", exc_info=True)
            logger.warning("Reinitializing corrupted config")
            _initialize_config_file()
            return {STREAMS_KEY: []}
            
        except Exception as e:
            logger.error(f"Config load error: {e}", exc_info=True)
            _initialize_config_file()
            return {STREAMS_KEY: []}


# ============================================================================
# Configuration Saving
# ============================================================================

def save_streams(config: dict[str, Any]) -> None:
    """Save config with atomic write.
    
    Args:
        config: Config dict with 'streams' key
        
    Raises:
        ValueError: Invalid structure
        IOError: Write failure
    """
    # Validate
    if not isinstance(config, dict):
        raise ValueError("Config must be dict")
    
    if STREAMS_KEY not in config:
        config[STREAMS_KEY] = []
    
    if not isinstance(config[STREAMS_KEY], list):
        raise ValueError("Streams must be list")
    
    # Normalize order field
    normalized = config.copy()
    normalized[STREAMS_KEY] = _normalize_stream_order(config[STREAMS_KEY])
    
    # Dry-run: in-memory
    if _DRY_RUN_MODE:
        with _config_lock:
            global _in_memory_config
            _in_memory_config = normalized.copy()
            logger.debug(f"Saved {len(normalized[STREAMS_KEY])} stream(s) to memory")
        return
    
    _ensure_config_dir()
    
    # Atomic write
    with _config_lock:
        temp_path = None
        try:
            # Create temp file in same dir (ensures atomic rename)
            fd, temp_path = tempfile.mkstemp(
                dir=CONFIG_DIR,
                prefix=".config_",
                suffix=".yml.tmp"
            )
            
            # Write to temp
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    normalized,
                    f,
                    default_flow_style=False,
                    sort_keys=True,
                    allow_unicode=True
                )
            
            # Atomic rename
            _atomic_rename(temp_path, CONFIG_PATH)
            
            logger.debug(f"Saved {len(normalized[STREAMS_KEY])} stream(s)")
            
        except Exception as e:
            logger.error(f"Config save failed: {e}", exc_info=True)
            
            # Cleanup temp
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as cleanup_err:
                    logger.warning(f"Temp cleanup failed: {cleanup_err}")
            
            raise


def _normalize_stream_order(streams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize order field to 0, 1, 2, ..."""
    normalized = []
    for idx, stream in enumerate(streams):
        stream_copy = stream.copy()
        stream_copy["order"] = idx
        normalized.append(stream_copy)
    return normalized


def _atomic_rename(src: str | Path, dst: str | Path) -> None:
    """Atomic rename (POSIX) or best-effort (Windows)."""
    src_path = Path(src)
    dst_path = Path(dst)
    
    if os.name == "nt":
        # Windows: remove target first (not atomic)
        if dst_path.exists():
            dst_path.unlink()
    
    src_path.rename(dst_path)


# ============================================================================
# GPU Detection
# ============================================================================

def get_gpu_backend() -> str:
    """Get GPU backend from environment.
    
    Returns:
        "nvidia", "amd", "intel", or "none"
    """
    backend = os.getenv("GPU_BACKEND_DETECTED", "none").lower()
    
    valid = {"nvidia", "amd", "intel", "none"}
    if backend not in valid:
        logger.warning(f"Invalid GPU_BACKEND_DETECTED '{backend}', using 'none'")
        return "none"
    
    return backend


# ============================================================================
# Module Initialization
# ============================================================================

_ensure_config_dir()

if _DRY_RUN_MODE:
    logger.info("Config: DRY_RUN mode (in-memory)")
else:
    logger.info(f"Config: Production mode ({CONFIG_PATH})")
