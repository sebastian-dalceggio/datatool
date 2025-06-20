"""Pytest conftest.py for shared fixtures."""

import pytest

from datatool.config import Config


@pytest.fixture
def mock_config(tmp_path) -> Config:
    """Provides a mock Config object."""
    storage_path = tmp_path / "storage"
    storage_path.mkdir(exist_ok=True)
    return Config(storage_parent_path=storage_path, process_name="test_process")
