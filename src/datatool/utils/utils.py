"""General utility functions for the datatool package."""


def incremental_counter():
    """A generator that yields incrementing integers, starting from 0.

    Yields:
        int: The next integer in the sequence.
    """
    count = 0
    while True:
        yield count
        count += 1
