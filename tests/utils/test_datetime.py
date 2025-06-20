"""Tests for the datatool.utils.datetime module."""

import pytest
import pendulum

from datatool.utils.datetime import get_datetime_from_str


def test_get_datetime_from_str_valid():
    """Test get_datetime_from_str with valid input."""
    dt_str = "2023-01-15 10:30:00"
    fmt = "YYYY-MM-DD HH:mm:ss"
    expected_dt = pendulum.datetime(2023, 1, 15, 10, 30, 0)
    assert get_datetime_from_str(dt_str, fmt) == expected_dt


def test_get_datetime_from_str_invalid_format():
    """Test get_datetime_from_str with an invalid format string for the input."""
    with pytest.raises(
        ValueError
    ):  # pendulum.exceptions.ParserError inherits ValueError
        get_datetime_from_str("2023/01/15", "YYYY-MM-DD")
