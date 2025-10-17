"""JSON logging configuration for the application."""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as newline-delimited JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from the record's __dict__
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName", 
                          "levelname", "levelno", "lineno", "module", "msecs", 
                          "message", "pathname", "process", "processName", 
                          "relativeCreated", "thread", "threadName", "exc_info", 
                          "exc_text", "stack_info", "taskName"]:
                log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False)


def configure_logging() -> None:
    """Configure JSON logging based on LOG_LEVEL environment variable.
    
    Default level is INFO. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    """
    log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add JSON handler to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Configure FastAPI/Uvicorn loggers
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
