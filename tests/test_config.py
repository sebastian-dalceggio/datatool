"""Tests for the datatool.config module."""

from io import StringIO
import logging

import pytest
import pendulum

from datatool.config import Config, _NULL_LOGGER
from datatool.utils.datetime import get_datetime_from_str


def test_config_initialization_defaults(tmp_path):
    """Test Config initialization with default values."""
    storage_path = tmp_path / "storage"
    config = Config(storage_parent_path=str(storage_path))

    assert isinstance(config.datetime, pendulum.DateTime)
    assert config.datetime_fmt == "YYYY-MM-DD HH:mm:ss+00:00"
    assert config.process_name is None
    assert config.logger == _NULL_LOGGER
    assert config.storage_parent_path == storage_path
    assert config.storage_folder_fmt == "YYYY/MM/DD"
    assert config.storage_folders == config.datetime.format("YYYY/MM/DD")
    assert config.environment == "dev"


def test_config_initialization_custom_values(tmp_path):
    """Test Config initialization with custom values."""
    storage_path = tmp_path / "custom_storage"
    dt = pendulum.datetime(2023, 1, 1, 12, 0, 0, tz="UTC")
    dt_fmt = "YYYY-MM-DD"
    process_name = "custom_process"
    log_stream = StringIO()
    storage_folder_fmt = "YYYY_MM"
    environment = "prod"

    config = Config(
        storage_parent_path=storage_path,
        datetime=dt,
        datetime_fmt=dt_fmt,
        process_name=process_name,
        stream=log_stream,
        storage_folder_fmt=storage_folder_fmt,
        environment=environment,
    )

    assert config.datetime == dt
    assert config.datetime_fmt == dt_fmt
    assert config.process_name == process_name
    assert config.logger is not _NULL_LOGGER
    assert config.logger.name == "datatool.config"
    assert config.storage_parent_path == storage_path
    assert config.storage_folder_fmt == storage_folder_fmt
    assert config.storage_folders == dt.format(storage_folder_fmt)
    assert config.environment == environment


def test_config_datetime_string_parsing(tmp_path):
    """Test Config datetime parsing from string."""
    storage_path = tmp_path / "storage"
    dt_str = "2023-03-15 10:30:00+00:00"
    dt_fmt = "YYYY-MM-DD HH:mm:ssZ"
    config = Config(
        storage_parent_path=str(storage_path), datetime=dt_str, datetime_fmt=dt_fmt
    )
    expected_dt = get_datetime_from_str(dt_str, dt_fmt)
    assert config.datetime == expected_dt


def test_config_type_errors(tmp_path):
    """Test Config raises TypeError for invalid input types."""
    storage_path = tmp_path / "storage"
    with pytest.raises(
        TypeError, match="datetime should be pendulum.DateTime, str, or None"
    ):
        Config(storage_parent_path=str(storage_path), datetime=123)

    with pytest.raises(TypeError, match="should be PathType or str"):
        Config(storage_parent_path=12345)


def test_config_datetime_none(tmp_path):
    """Test Config initialization with datetime=None uses current time."""
    storage_path = tmp_path / "storage"
    now = pendulum.now()
    with pendulum.travel_to(now):
        config = Config(storage_parent_path=str(storage_path), datetime=None)
        assert config.datetime == now


def test_config_with_log_file(tmp_path):
    """Test Config logger setup with a log file path."""
    log_file = tmp_path / "test.log"
    config = Config(storage_parent_path=tmp_path, log_file_path=log_file)
    assert config.logger is not _NULL_LOGGER
    assert any(isinstance(h, logging.FileHandler) for h in config.logger.handlers)
    file_handler = next(
        h for h in config.logger.handlers if isinstance(h, logging.FileHandler)
    )
    assert file_handler.baseFilename == str(log_file)
    config.logger.info("test message")
    assert log_file.exists()
    assert "test message" in log_file.read_text()


def test_get_file_storage_path(mock_config):
    """Test get_file_storage_path method."""
    config = mock_config
    file_name = "data.txt"
    subdir = "raw"
    expected_path = (
        config.storage_parent_path / subdir / config.storage_folders / file_name
    )
    assert config.get_file_storage_path(file_name, subdir) == expected_path

    hidden_file_name = ".hidden_data.txt"
    expected_hidden_path = (
        config.storage_parent_path / subdir / config.storage_folders / hidden_file_name
    )
    assert (
        config.get_file_storage_path(hidden_file_name, subdir) == expected_hidden_path
    )


def test_get_file_storage_path_special_dotfile(mock_config):
    """Test get_file_storage_path for special dotfiles (e.g., '.log')."""
    config = mock_config
    special_dot_file = ".log"
    subdir = "logs"
    # Expected: storage_parent_path/subdir/YYYY/MM/DD.log
    expected_path = (
        config.storage_parent_path
        / subdir
        / f"{config.storage_folders}{special_dot_file}"
    )
    assert config.get_file_storage_path(special_dot_file, subdir) == expected_path
