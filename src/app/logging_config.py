"""Structured logging with credential redaction.

Provides clean logs in format: timestamp | level | message | logger

Switch to JSON with: LOG_FORMAT=json

Security:
    Automatically redacts RTSP credentials from all log messages.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Final

# ============================================================================
# Constants
# ============================================================================

RTSP_CREDENTIAL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r'rtsp://([^:]+):([^@]+)@',
    re.IGNORECASE
)
"""Matches RTSP URLs with credentials (rtsp://user:pass@host)."""

STANDARD_LOG_ATTRIBUTES: Final[set[str]] = {
    "name", "msg", "args", "created", "filename", "funcName",
    "levelname", "levelno", "lineno", "module", "msecs",
    "message", "pathname", "process", "processName",
    "relativeCreated", "thread", "threadName", "exc_info",
    "exc_text", "stack_info", "taskName"
}
"""Standard logging attributes to exclude from JSON extra fields."""

# ============================================================================
# Credential Redaction
# ============================================================================

def redact_credentials(message: str) -> str:
    """Redact RTSP credentials from log messages.
    
    Replaces rtsp://user:pass@host with rtsp://***:***@host
    
    Args:
        message: Log message
        
    Returns:
        Message with credentials masked
    """
    return RTSP_CREDENTIAL_PATTERN.sub(r'rtsp://***:***@', message)


# ============================================================================
# Formatters
# ============================================================================

class TextFormatter(logging.Formatter):
    """Clean text formatter with aligned columns.
    
    Format: timestamp | logger | level | message
    
    Example:
        2025-10-28T05:10:23.456Z | app.main                    | INFO     | Server starting
        2025-10-28T05:10:24.789Z | app.services.streams        | ERROR    | Failed
    """
    
    LOGGER_WIDTH = 40
    """Logger name column width."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as aligned text."""
        # Redact message
        message = redact_credentials(record.getMessage())
        
        # ISO 8601 UTC timestamp
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        
        # Pad logger name (truncate with ellipsis if too long)
        logger_name = record.name
        if len(logger_name) > self.LOGGER_WIDTH:
            logger_name = "..." + logger_name[-(self.LOGGER_WIDTH-3):]
        logger_padded = logger_name.ljust(self.LOGGER_WIDTH)
        
        # Pad level (8 chars)
        level_padded = record.levelname.ljust(8)
        
        # Build line
        log_line = f"{timestamp} | {logger_padded} | {level_padded} | {message}"
        
        # Add exception if present
        if record.exc_info:
            exception_text = self.formatException(record.exc_info)
            log_line += f"\n{redact_credentials(exception_text)}"
        
        return log_line


class JSONFormatter(logging.Formatter):
    """JSON formatter for log aggregation systems (ELK, Splunk, CloudWatch).
    
    Produces NDJSON (newline-delimited JSON) with:
    - timestamp: ISO 8601 UTC
    - level: Log level
    - message: Redacted message
    - logger: Hierarchical logger name
    - exception: Stack trace if present
    - extra_*: Additional fields from log record
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        message = redact_credentials(record.getMessage())
        
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": message,
            "logger": record.name,
        }
        
        # Add exception
        if record.exc_info:
            log_data["exception"] = redact_credentials(self.formatException(record.exc_info))
        
        # Add stack trace
        if record.stack_info:
            log_data["stack_info"] = redact_credentials(record.stack_info)
        
        # Add extra fields (prefixed to avoid collisions)
        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_ATTRIBUTES:
                if isinstance(value, str):
                    value = redact_credentials(value)
                log_data[f"extra_{key}"] = value
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


# ============================================================================
# Configuration
# ============================================================================

def get_log_level() -> int:
    """Get log level from environment.
    
    Returns:
        Logging level constant (e.g., logging.INFO)
    """
    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if level_str not in valid_levels:
        logging.warning(f"Invalid LOG_LEVEL '{level_str}', using INFO")
        return logging.INFO
    
    return getattr(logging, level_str)


def get_log_format() -> str:
    """Get log format from environment.
    
    Returns:
        "text" or "json"
    """
    format_str = os.getenv("LOG_FORMAT", "text").lower()
    
    if format_str not in {"text", "json"}:
        logging.warning(f"Invalid LOG_FORMAT '{format_str}', using text")
        return "text"
    
    return format_str


def configure_logging() -> None:
    """Configure structured logging with credential redaction.
    
    Sets up:
    - Root logger with text or JSON formatting
    - Console (stdout) handler
    - Credential redaction for security
    - Uvicorn logger integration
    
    Environment:
        LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
        LOG_FORMAT: text, json (default: text)
    """
    log_level = get_log_level()
    log_format = get_log_format()
    
    # Configure root logger
    root = logging.getLogger()
    root.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Create console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    
    # Set formatter
    if log_format == "json":
        console.setFormatter(JSONFormatter())
    else:
        console.setFormatter(TextFormatter())
    
    root.addHandler(console)
    
    # Fix Uvicorn loggers to use our formatter
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.handlers.clear()
        logger.propagate = True
    
    # Configure FastAPI logger
    fastapi = logging.getLogger("fastapi")
    fastapi.setLevel(log_level)
    fastapi.propagate = True
    
    # Log init
    root.info(f"Logging: level={logging.getLevelName(log_level)}, format={log_format}")


def setup_logging() -> None:
    """Setup logging (alias for backward compatibility)."""
    configure_logging()
