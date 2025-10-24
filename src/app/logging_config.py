"""Structured JSON logging configuration with credential redaction."""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Final

# ============================================================================
# Constants
# ============================================================================

# Regex pattern to match RTSP URLs with credentials (rtsp://user:pass@...)
RTSP_CREDENTIAL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'rtsp://([^:]+):([^@]+)@',
    re.IGNORECASE
)

# Standard logging record attributes to exclude from extra fields
STANDARD_LOG_ATTRIBUTES: Final[set[str]] = {
    "name", "msg", "args", "created", "filename", "funcName",
    "levelname", "levelno", "lineno", "module", "msecs",
    "message", "pathname", "process", "processName",
    "relativeCreated", "thread", "threadName", "exc_info",
    "exc_text", "stack_info", "taskName"
}


class LogLevel(str, Enum):
    """Supported logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ============================================================================
# Credential Redaction
# ============================================================================

def redact_credentials(message: str) -> str:
    """Redact credentials from RTSP URLs in log messages.
    
    Replaces credentials in RTSP URLs (rtsp://user:pass@host)
    with masked placeholders (rtsp://***:***@host).
    
    Args:
        message: Log message that may contain RTSP URLs with credentials
        
    Returns:
        Message with credentials replaced by ***:***
        
    Example:
        >>> redact_credentials("rtsp://admin:secret@192.168.1.100/stream")
        'rtsp://***:***@192.168.1.100/stream'
    """
    return RTSP_CREDENTIAL_PATTERN.sub(r'rtsp://***:***@', message)


def log_ffmpeg_stderr(stream_id: str, stderr_data: bytes) -> None:
    """Log FFmpeg stderr output with credential redaction.
    
    Args:
        stream_id: Stream identifier for logger namespacing
        stderr_data: Raw stderr bytes from FFmpeg process
    """
    try:
        message = stderr_data.decode('utf-8', errors='ignore').strip()
        if message:
            logger = logging.getLogger(f"ffmpeg.{stream_id}")
            logger.warning(f"FFmpeg stderr: {redact_credentials(message)}")
    except Exception as e:
        logging.getLogger("ffmpeg").error(
            f"Failed to log FFmpeg stderr for stream {stream_id}: {e}"
        )


# ============================================================================
# JSON Formatter
# ============================================================================

class JSONFormatter(logging.Formatter):
    """Format log records as structured JSON with credential redaction.
    
    Produces newline-delimited JSON (NDJSON) for easy parsing by log
    aggregation systems like ELK, Splunk, or CloudWatch.
    
    Each log record is formatted as a single-line JSON object with:
    - timestamp: ISO 8601 formatted UTC timestamp
    - level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Logger name (hierarchical, e.g., "app.api.streams")
    - message: Log message with redacted credentials
    - exception: Full exception traceback if present
    - extra_*: Any additional fields from the log record
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string.
        
        Args:
            record: Log record to format
            
        Returns:
            Single-line JSON string
        """
        # Get and redact the message
        message = record.getMessage()
        message = redact_credentials(message)
        
        # Build base log structure
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        
        # Add exception information if present
        if record.exc_info:
            exception_text = self.formatException(record.exc_info)
            log_data["exception"] = redact_credentials(exception_text)
        
        # Add stack trace if available
        if record.stack_info:
            log_data["stack_info"] = redact_credentials(record.stack_info)
        
        # Add extra fields from log record (prefixed to avoid collisions)
        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_ATTRIBUTES:
                # Redact string values
                if isinstance(value, str):
                    value = redact_credentials(value)
                log_data[f"extra_{key}"] = value
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


# ============================================================================
# Configuration
# ============================================================================

def get_log_level() -> int:
    """Get log level from environment with validation.
    
    Returns:
        Logging level constant (e.g., logging.INFO)
    """
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    try:
        # Validate against enum
        LogLevel(log_level_str)
        return getattr(logging, log_level_str)
    except (ValueError, AttributeError):
        logging.warning(f"Invalid LOG_LEVEL '{log_level_str}', defaulting to INFO")
        return logging.INFO


def configure_logging() -> None:
    """Configure structured JSON logging for the application.
    
    Sets up:
    - Root logger with JSON formatting
    - Console (stdout) handler for container-friendly logging
    - Log level from LOG_LEVEL environment variable
    - Credential redaction for security
    - Proper propagation for FastAPI/Uvicorn loggers
    
    Environment Variables:
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  Defaults to INFO if not set or invalid
    """
    log_level = get_log_level()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create and configure stdout handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # Configure FastAPI/Uvicorn loggers to use our format
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.propagate = True  # Use root logger's handlers
    
    # Log successful initialization
    root_logger.info(
        f"Logging configured: level={logging.getLevelName(log_level)}, "
        f"format=JSON, redaction=enabled"
    )


def setup_logging() -> None:
    """Setup logging (alias for configure_logging).
    
    Provided for backward compatibility and clearer naming.
    """
    configure_logging()


# ============================================================================
# Utility Functions
# ============================================================================

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)
