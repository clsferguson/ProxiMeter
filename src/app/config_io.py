"""Thread-safe YAML configuration management with atomic writes."""
from __future__ import annotations

import io
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Final

import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

CONFIG_DIR: Final[Path] = Path(os.getenv("CONFIG_DIR", "/app/config"))
CONFIG_PATH: Final[Path] = CONFIG_DIR / "config.yml"
STREAMS_KEY: Final[str] = "streams"

# CI/Testing mode: use in-memory storage instead of disk
_DRY_RUN_MODE: Final[bool] = os.getenv("CI_DRY_RUN", "").lower() in ("true", "1", "yes")

# Thread-safe in-memory storage for testing
_in_memory_config: dict[str, Any] = {STREAMS_KEY: []}
_config_lock = threading.RLock()


# ============================================================================
# Initialization
# ============================================================================

def _ensure_config_dir() -> None:
    """Ensure configuration directory exists."""
    if not _DRY_RUN_MODE:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _initialize_config_file() -> None:
    """Initialize configuration file with empty structure."""
    if not _DRY_RUN_MODE:
        logger.info(f"Initializing new configuration file: {CONFIG_PATH}")
        save_streams({STREAMS_KEY: []})


# ============================================================================
# Configuration Loading
# ============================================================================

def load_streams() -> dict[str, Any]:
    """Load configuration from storage.
    
    Returns:
        Configuration dict with 'streams' key containing list of streams.
        
    Example:
        >>> config = load_streams()
        >>> streams = config.get("streams", [])
    """
    # Dry-run mode: return in-memory copy
    if _DRY_RUN_MODE:
        with _config_lock:
            return _in_memory_config.copy()
    
    # Ensure config directory exists
    _ensure_config_dir()
    
    # Initialize if config doesn't exist
    if not CONFIG_PATH.exists():
        _initialize_config_file()
        return {STREAMS_KEY: []}
    
    # Load configuration with error recovery
    with _config_lock:
        try:
            with io.open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            # Ensure data is a dict
            if not isinstance(data, dict):
                logger.warning(
                    f"Invalid config format in {CONFIG_PATH}, reinitializing"
                )
                _initialize_config_file()
                return {STREAMS_KEY: []}
            
            # Ensure streams key exists and is a list
            if STREAMS_KEY not in data:
                data[STREAMS_KEY] = []
            elif not isinstance(data[STREAMS_KEY], list):
                logger.warning(
                    f"Invalid streams format in {CONFIG_PATH}, reinitializing"
                )
                data[STREAMS_KEY] = []
            
            return data
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {CONFIG_PATH}: {e}")
            _initialize_config_file()
            return {STREAMS_KEY: []}
            
        except Exception as e:
            logger.error(f"Error loading config from {CONFIG_PATH}: {e}")
            _initialize_config_file()
            return {STREAMS_KEY: []}


# ============================================================================
# Configuration Saving
# ============================================================================

def save_streams(config: dict[str, Any]) -> None:
    """Persist configuration to storage with atomic writes.
    
    Args:
        config: Configuration dict with 'streams' key
        
    Example:
        >>> config = load_streams()
        >>> config["streams"].append({"name": "Camera 1", ...})
        >>> save_streams(config)
    """
    # Validate input
    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary")
    
    if STREAMS_KEY not in config:
        config[STREAMS_KEY] = []
    
    if not isinstance(config[STREAMS_KEY], list):
        raise ValueError("Streams must be a list")
    
    # Normalize order field to be contiguous
    normalized_config = config.copy()
    normalized_config[STREAMS_KEY] = _normalize_stream_order(config[STREAMS_KEY])
    
    # Dry-run mode: update in-memory storage
    if _DRY_RUN_MODE:
        with _config_lock:
            global _in_memory_config
            _in_memory_config = normalized_config.copy()
        logger.debug("Saved config to in-memory storage (dry-run mode)")
        return
    
    # Ensure config directory exists
    _ensure_config_dir()
    
    # Atomic write with error recovery
    with _config_lock:
        temp_path = None
        try:
            # Create temp file in same directory for atomic rename
            fd, temp_path = tempfile.mkstemp(
                dir=CONFIG_DIR,
                prefix=".config_",
                suffix=".yml.tmp"
            )
            
            # Write to temp file
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    normalized_config,
                    f,
                    default_flow_style=False,
                    sort_keys=True,
                    allow_unicode=True
                )
            
            # Atomic rename (POSIX) or best-effort (Windows)
            _atomic_rename(temp_path, CONFIG_PATH)
            
            streams_count = len(normalized_config.get(STREAMS_KEY, []))
            logger.debug(f"Saved config with {streams_count} streams to {CONFIG_PATH}")
            
        except Exception as e:
            logger.error(f"Error saving config to {CONFIG_PATH}: {e}")
            # Clean up temp file on error
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            raise


def _normalize_stream_order(streams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize stream order field to be contiguous."""
    normalized = []
    for idx, stream in enumerate(streams):
        stream_copy = stream.copy()
        stream_copy["order"] = idx
        normalized.append(stream_copy)
    return normalized


def _atomic_rename(src: str | Path, dst: str | Path) -> None:
    """Atomically rename file (or best-effort on Windows)."""
    src_path = Path(src)
    dst_path = Path(dst)
    
    if os.name == "nt":
        # Windows: not truly atomic, remove target first
        if dst_path.exists():
            dst_path.unlink()
    
    src_path.rename(dst_path)


# ============================================================================
# GPU Detection
# ============================================================================

def get_gpu_backend() -> str:
    """Get detected GPU backend from environment."""
    backend = os.getenv("GPU_BACKEND_DETECTED", "none").lower()
    
    valid_backends = {"nvidia", "amd", "intel", "none"}
    if backend not in valid_backends:
        logger.warning(
            f"Invalid GPU_BACKEND_DETECTED value '{backend}', defaulting to 'none'"
        )
        return "none"
    
    return backend


# ============================================================================
# Utility Functions
# ============================================================================

def reset_config() -> None:
    """Reset configuration to empty state."""
    with _config_lock:
        if _DRY_RUN_MODE:
            global _in_memory_config
            _in_memory_config = {STREAMS_KEY: []}
            logger.info("Reset in-memory configuration")
            return
        
        # Backup existing config
        if CONFIG_PATH.exists():
            backup_path = CONFIG_PATH.with_suffix(".yml.backup")
            CONFIG_PATH.rename(backup_path)
            logger.info(f"Backed up config to {backup_path}")
        
        # Initialize fresh config
        _initialize_config_file()
        logger.info("Reset configuration to empty state")


def get_config_info() -> dict[str, Any]:
    """Get configuration metadata."""
    with _config_lock:
        if _DRY_RUN_MODE:
            return {
                "mode": "dry-run",
                "storage": "in-memory",
                "streams_count": len(_in_memory_config.get(STREAMS_KEY, []))
            }
        
        config = load_streams() if CONFIG_PATH.exists() else {STREAMS_KEY: []}
        return {
            "mode": "production",
            "storage": "file",
            "config_path": str(CONFIG_PATH),
            "config_dir": str(CONFIG_DIR),
            "exists": CONFIG_PATH.exists(),
            "streams_count": len(config.get(STREAMS_KEY, []))
        }


# ============================================================================
# Initialization
# ============================================================================

# Initialize on module import
_ensure_config_dir()

if _DRY_RUN_MODE:
    logger.info("Configuration: DRY_RUN mode (in-memory storage)")
else:
    logger.info(f"Configuration: Production mode (file: {CONFIG_PATH})")
