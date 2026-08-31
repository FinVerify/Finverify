"""
Tests for Centralized Logging Configuration
============================================
Verifies logging_config.py behavior:
- Standard format logging
- JSON structured format logging
- Environment variable configuration
- Idempotency of setup_logging()
"""

import io
import json
import logging
import pytest
from app.logging_config import setup_logging, LoggingSettings, JSONFormatter


def test_default_setup_logging():
    """Verify default logging setup configures root logger."""
    stream = io.StringIO()
    logger = setup_logging(log_level="INFO", json_format=False, stream=stream)

    assert logger.level == logging.INFO
    test_logger = logging.getLogger("test_logger")
    test_logger.info("Hello World")

    output = stream.getvalue()
    assert "[INFO] test_logger: Hello World" in output


def test_json_formatting():
    """Verify JSON formatting outputs valid JSON with expected fields."""
    stream = io.StringIO()
    setup_logging(log_level="DEBUG", json_format=True, stream=stream)

    test_logger = logging.getLogger("test_json")
    test_logger.info("Test JSON log message", extra={"user_id": "usr_123"})

    output = stream.getvalue().strip()
    log_data = json.loads(output)

    assert log_data["level"] == "INFO"
    assert log_data["logger"] == "test_json"
    assert log_data["message"] == "Test JSON log message"
    assert log_data["user_id"] == "usr_123"
    assert "timestamp" in log_data


def test_log_level_filtering():
    """Verify log messages below set level are filtered out."""
    stream = io.StringIO()
    setup_logging(log_level="WARNING", json_format=False, stream=stream)

    test_logger = logging.getLogger("test_filter")
    test_logger.info("This should not be logged")
    test_logger.warning("This should be logged")

    output = stream.getvalue()
    assert "This should not be logged" not in output
    assert "This should be logged" in output


def test_idempotent_setup_logging():
    """Verify repeated calls do not duplicate log handlers."""
    stream = io.StringIO()
    setup_logging(log_level="INFO", json_format=False, stream=stream)
    setup_logging(log_level="INFO", json_format=False, stream=stream)

    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 1


def test_env_var_configuration(monkeypatch):
    """Verify environment variables dictate logging settings."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT_JSON", "true")

    settings = LoggingSettings()
    assert settings.log_level == "DEBUG"
    assert settings.is_json is True
    assert settings.numeric_level == logging.DEBUG
