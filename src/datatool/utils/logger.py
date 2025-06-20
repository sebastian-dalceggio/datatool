"""Utility functions for configuring and retrieving loggers."""

from typing import IO, TextIO
import logging
from pathlib import Path


def get_logger(
    name: str,
    logging_level: int | str,
    log_file_path: Path | str | None = None,
    stream: IO[str] | TextIO | None = None,
) -> logging.Logger:
    """Configures and returns a logger instance.

    Args:
        name: The name of the logger.
        logging_level: The logging level (e.g., logging.INFO, "DEBUG").
        log_file_path: Optional path to a file for logging.
        stream: Optional IO stream for logging (e.g., sys.stdout).

    Returns:
        A configured logging.Logger instance.

    Raises:
        ValueError: If neither log_file_path nor stream is provided and the logger has no handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging_level)
    formatter = logging.Formatter(
        "%(asctime)s:%(name)s:%(levelname)s:%(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if log_file_path is None and stream is None and not logger.handlers:
        raise ValueError(
            "Neither log_file_path nor stream provided and logger has no handlers."
        )
    if log_file_path:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    if stream:
        stream_handler = logging.StreamHandler(stream)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    return logger
