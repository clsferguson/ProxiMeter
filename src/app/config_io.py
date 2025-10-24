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
_in_memory_streams: list[dict[str, Any]] = []
_config_lock = threading.RLock()  # Reentrant lock for nested calls


# ============================================================================
# Initialization
# ============================================================================

def _ensure_config_dir() -> None:
    """Ensure configuration directory exists.
    
    Creates the config directory if it doesn't exist.
    Safe to call multiple times (idempotent).
    """
    if not _DRY_RUN_MODE:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _initialize_config_file() -> None:
    """Initialize configuration file with empty structure.
    
    Creates a new config file with empty streams list.
    Only called when config file doesn't exist.
    """
    if not _DRY_RUN_MODE:
        logger.info(f"Initializing new configuration file: {CONFIG_PATH}")
        save_streams([])


# ============================================================================
# Configuration Loading
# ============================================================================

def load_streams() -> list[dict[str, Any]]:
    """Load streams from configuration storage.
    
    In production: Loads from YAML file with automatic error recovery.
    In dry-run mode: Returns in-memory copy for testing.
    
    Returns:
        List of stream dictionaries, sorted by order field.
        Returns empty list if file is missing or malformed.
        
    Example:
        >>> streams = load_streams()
        >>> for stream in streams:
        ...     print(stream['name'], stream['rtsp_url'])
    """
    # Dry-run mode: return in-memory copy
    if _DRY_RUN_MODE:
        with _config_lock:
            return _in_memory_streams.copy()
    
    # Ensure config directory exists
    _ensure_config_dir()
    
    # Initialize if config doesn't exist
    if not CONFIG_PATH.exists():
        _initialize_config_file()
        return []
    
    # Load configuration with error recovery
    with _config_lock:
        try:
            with io.open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            streams = data.get(STREAMS_KEY, [])
            
            # Validate streams is a list
            if not isinstance(streams, list):
                logger.warning(
                    f"Invalid streams format in {CONFIG_PATH}, reinitializing"
                )
                _initialize_config_file()
                return []
            
            return streams
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {CONFIG_PATH}: {e}")
            _initialize_config_file()
            return []
            
        except Exception as e:
            logger.error(f"Error loading config from {CONFIG_PATH}: {e}")
            _initialize_config_file()
            return []


# ============================================================================
# Configuration Saving
# ============================================================================

def save_streams(streams: list[dict[str, Any]]) -> None:
    """Persist streams to configuration storage with atomic writes.
    
    In production: Uses atomic write pattern (write to temp, then rename).
    In dry-run mode: Updates in-memory storage for testing.
    
    Automatically normalizes order field to be contiguous (0, 1, 2, ...).
    
    Args:
        streams: List of stream dictionaries to persist
        
    Raises:
        OSError: If file operations fail
        yaml.YAMLError: If YAML serialization fails
        
    Example:
        >>> streams = load_streams()
        >>> streams.append({"name": "Camera 1", "rtsp_url": "rtsp://..."})
        >>> save_streams(streams)
    """
    # Normalize order field to be contiguous
    normalized_streams = _normalize_stream_order(streams)
    
    # Dry-run mode: update in-memory storage
    if _DRY_RUN_MODE:
        with _config_lock:
            global _in_memory_streams
            _in_memory_streams = normalized_streams.copy()
        logger.debug("Saved streams to in-memory storage (dry-run mode)")
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
                    {STREAMS_KEY: normalized_streams},
                    f,
                    default_flow_style=False,
                    sort_keys=True,
                    allow_unicode=True
                )
            
            # Atomic rename (POSIX) or best-effort (Windows)
            _atomic_rename(temp_path, CONFIG_PATH)
            
            logger.debug(f"Saved {len(normalized_streams)} streams to {CONFIG_PATH}")
            
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
    """Normalize stream order field to be contiguous.
    
    Args:
        streams: List of stream dictionaries
        
    Returns:
        List with normalized order field (0, 1, 2, ...)
    """
    normalized = []
    for idx, stream in enumerate(streams):
        stream_copy = stream.copy()
        stream_copy["order"] = idx
        normalized.append(stream_copy)
    return normalized


def _atomic_rename(src: str | Path, dst: str | Path) -> None:
    """Atomically rename file (or best-effort on Windows).
    
    Args:
        src: Source file path
        dst: Destination file path
    """
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
    """Get detected GPU backend from environment.
    
    Returns:
        GPU backend type: "nvidia", "amd", "intel", or "none"
        
    Example:
        >>> backend = get_gpu_backend()
        >>> if backend != "none":
        ...     print(f"GPU acceleration available: {backend}")
    """
    backend = os.getenv("GPU_BACKEND_DETECTED", "none").lower()
    
    # Validate backend value
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
    """Reset configuration to empty state.
    
    Useful for testing or emergency recovery.
    Creates a backup of existing config if present.
    """
    with _config_lock:
        if _DRY_RUN_MODE:
            global _in_memory_streams
            _in_memory_streams = []
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
    """Get configuration metadata.
    
    Returns:
        Dictionary with config location, mode, and stats
    """
    with _config_lock:
        if _DRY_RUN_MODE:
            return {
                "mode": "dry-run",
                "storage": "in-memory",
                "streams_count": len(_in_memory_streams)
            }
        
        return {
            "mode": "production",
            "storage": "file",
            "config_path": str(CONFIG_PATH),
            "config_dir": str(CONFIG_DIR),
            "exists": CONFIG_PATH.exists(),
            "streams_count": len(load_streams()) if CONFIG_PATH.exists() else 0
        }


# ============================================================================
# Initialization
# ============================================================================

# Initialize on module import (safe, idempotent)
_ensure_config_dir()

# Log configuration info
if _DRY_RUN_MODE:
    logger.info("Configuration: DRY_RUN mode (in-memory storage)")
else:
    logger.info(f"Configuration: Production mode (file: {CONFIG_PATH})")
