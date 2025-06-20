"""Datetime utility functions."""

import pendulum


def get_datetime_from_str(datetime: str, format: str) -> pendulum.DateTime:
    """Converts a datetime string to a pendulum.DateTime object.

    Args:
        datetime: The datetime string to convert.
        format: The format string of the input datetime string.

    Returns:
        A pendulum.DateTime object.
    """
    return pendulum.from_format(datetime, format)
