"""
Logging Configuration
=====================
Centralized logging setup for FinVerify Terminal.
Supports standard formatted console logging and structured JSON logging.
Configurable via environment variables (LOG_LEVEL, LOG_FORMAT, LOG_FORMAT_JSON)
or explicit parameters passed to `setup_logging()`.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field


class LoggingSettings(BaseModel):
    """Logging settings schema backed by environment variables."""

    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )
    log_format: str = Field(
        default_factory=lambda: os.getenv("LOG_FORMAT", "text").lower()
    )
    log_format_json: bool = Field(
        default_factory=lambda: os.getenv("LOG_FORMAT_JSON", "false").lower() in ("true", "1", "yes")
    )

    @property
    def is_json(self) -> bool:
        return self.log_format_json or self.log_format == "json"

    @property
    def numeric_level(self) -> int:
        return getattr(logging, self.log_level.upper(), logging.INFO)


class JSONFormatter(logging.Formatter):
    """Formatter that outputs single-line JSON objects for log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_obj["stack_info"] = self.formatStack(record.stack_info)

        # Include custom extra fields if passed in log call
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "taskName",
        }
        for key, val in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                try:
                    json.dumps(val)
                    log_obj[key] = val
                except (TypeError, ValueError):
                    log_obj[key] = str(val)

        return json.dumps(log_obj)


def get_logging_settings() -> LoggingSettings:
    """Instantiate logging settings from environment."""
    return LoggingSettings()


def setup_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    json_format: Optional[bool] = None,
    stream: Optional[Any] = None,
) -> logging.Logger:
    """
    Configure root logging with specified or environment-driven level and format.

    Args:
        log_level: Logging level string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
        log_format: Logging format mode ('text' or 'json').
        json_format: Boolean flag to force JSON format.
        stream: Target stream (defaults to sys.stdout).

    Returns:
        Root logger instance.
    """
    settings = get_logging_settings()

    # Override settings with explicit arguments if provided
    effective_level_str = (log_level or settings.log_level).upper()
    numeric_level = getattr(logging, effective_level_str, logging.INFO)

    use_json = json_format if json_format is not None else settings.is_json
    if log_format is not None:
        use_json = log_format.lower() == "json" or use_json

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicate log messages (idempotent)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Create stream handler
    console_handler = logging.StreamHandler(stream or sys.stdout)
    console_handler.setLevel(numeric_level)

    if use_json:
        formatter: logging.Formatter = JSONFormatter()
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        datefmt = "%Y-%m-%dT%H:%M:%S%z"
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    return root_logger
