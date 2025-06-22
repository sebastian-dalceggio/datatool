"""Tests for the datatool.utils.utils module."""

from datatool.utils.utils import incremental_counter


def test_incremental_counter():
    """Tests the incremental_counter generator."""
    counter = incremental_counter()
    assert next(counter) == 0
    assert next(counter) == 1
    assert next(counter) == 2
