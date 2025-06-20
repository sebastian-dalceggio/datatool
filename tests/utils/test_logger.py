"""Tests for the datatool.utils.logger module."""

import pytest
import logging
from io import StringIO
from pathlib import Path

from datatool.utils.logger import get_logger


def test_get_logger_with_file(tmp_path: Path):
    """Test get_logger with a file handler."""
    log_file = tmp_path / "test.log"
    logger = get_logger("test_file_logger", logging.INFO, log_file_path=log_file)

    assert logger.name == "test_file_logger"
    assert logger.level == logging.INFO
    assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

    logger.info("Test message to file")
    assert log_file.exists()
    with open(log_file, "r") as f:
        content = f.read()
        assert "Test message to file" in content


def test_get_logger_with_stream():
    """Test get_logger with a stream handler."""
    stream = StringIO()
    logger = get_logger("test_stream_logger", logging.DEBUG, stream=stream)

    assert logger.name == "test_stream_logger"
    assert logger.level == logging.DEBUG
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    logger.debug("Test message to stream")
    assert "Test message to stream" in stream.getvalue()


def test_get_logger_with_file_and_stream(tmp_path: Path):
    """Test get_logger with both file and stream handlers."""
    log_file = tmp_path / "test_both.log"
    stream = StringIO()
    logger = get_logger(
        "test_both_logger", logging.WARNING, log_file_path=log_file, stream=stream
    )

    assert len(logger.handlers) == 2
    assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    logger.warning("Test message to both")
    assert log_file.exists()
    with open(log_file, "r") as f:
        assert "Test message to both" in f.read()
    assert "Test message to both" in stream.getvalue()


def test_get_logger_no_handler_error():
    """Test get_logger raises ValueError if no handlers are configured and none provided."""
    # Ensure the logger doesn't have pre-existing handlers from other tests
    logger_name = "test_no_handler_logger"
    # Remove any existing handlers for this logger name to ensure clean state
    logging.getLogger(logger_name).handlers = []

    with pytest.raises(ValueError, match="Neither log_file_path nor stream provided"):
        get_logger(logger_name, logging.INFO)
