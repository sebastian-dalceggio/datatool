"""Configuration module for datatool.

Provides the Config class for managing application settings.
"""

from typing import Literal, IO, TextIO
import logging
from pathlib import Path

import pendulum

from datatool.types import PathType
from datatool.paths.paths import get_path_from_str
from datatool.utils.logger import get_logger
from datatool.utils.datetime import get_datetime_from_str


_NULL_LOGGER = logging.getLogger("datatool.null")
_NULL_LOGGER.addHandler(logging.NullHandler())
_NULL_LOGGER.propagate = False


class Config:
    """Manages configuration settings for data processing tasks.

    Attributes:
        datetime_fmt (str): The format string for datetime objects.
        datetime (pendulum.DateTime): The current datetime for the process.
        process_name (str | None): The name of the current process.
        logger (logging.Logger): Logger instance for the application.
        storage_parent_path (PathType): The base path for storing files (local, cloud, or SSH).
        storage_folder_fmt (str): The format string for creating date-based subfolders.
        storage_folders (str): The formatted string representing date-based subfolders.
        environment (Literal["dev", "test", "prod"]): The deployment environment.
    """

    def __init__(
        self,
        storage_parent_path: PathType | str,
        datetime: pendulum.DateTime | str | None = None,
        datetime_fmt: str = "YYYY-MM-DD HH:mm:ss+00:00",
        process_name: str | None = None,
        log_file_path: Path | str | None = None,
        stream: IO[str] | TextIO | None = None,
        storage_folder_fmt: str = "YYYY/MM/DD",
        environment: Literal["dev", "test", "prod"] = "dev",
    ) -> None:
        """Initializes the Config object.

        Args:
            storage_parent_path: The base path for storing files.
            datetime: The datetime for the
                process. Can be a pendulum.DateTime, a string, or None.
                If None, it defaults to the current time.
            datetime_fmt: The format string for datetime objects.
            process_name: The name of the current process.
            log_file_path: Path to the log file.
            stream: IO stream for logging.
            storage_folder_fmt: Format string for date-based
                subfolders.
            environment: The deployment environment ('dev', 'test', 'prod').

        Raises:
            TypeError: If `datetime` or `storage_parent_path` have an invalid type.
        """

        self.datetime_fmt = datetime_fmt
        effective_datetime = datetime
        if effective_datetime is None:
            effective_datetime = pendulum.now()

        if isinstance(effective_datetime, pendulum.DateTime):
            self.datetime = effective_datetime
        elif isinstance(effective_datetime, str):
            self.datetime = get_datetime_from_str(effective_datetime, self.datetime_fmt)
        else:
            raise TypeError(
                "datetime should be pendulum.DateTime, str, or None. "
                f"Got {type(effective_datetime)}"
            )
        self.process_name = process_name
        if log_file_path or stream:
            self.logger = get_logger(
                __name__, logging.INFO, log_file_path=log_file_path, stream=stream
            )
        else:
            self.logger = _NULL_LOGGER
        if isinstance(storage_parent_path, PathType):
            self.storage_parent_path = storage_parent_path
        elif isinstance(storage_parent_path, str):
            self.storage_parent_path = get_path_from_str(storage_parent_path)
        else:
            raise TypeError(
                "storage_parent_path should be PathType or str. "
                f"Got {type(storage_parent_path)}"
            )
        self.storage_folder_fmt = storage_folder_fmt
        self.storage_folders = f"{self.datetime.format(self.storage_folder_fmt)}"
        self.environment = environment

    def get_file_storage_path(self, file_name: str, subdir: str) -> PathType:
        """
        Constructs the full storage path for a given file name and subdirectory.

        The path is constructed based on the `storage_parent_path`, `subdir`,
        and date-based `storage_folders`.

        A special case exists for `file_name` starting with a single dot:
        If `file_name` is, e.g., ".txt", the resulting path will be
        `storage_parent_path/subdir/YYYY/MM/DD.txt`.
        Otherwise, for a `file_name` like "data.txt", the path will be
        `storage_parent_path/subdir/YYYY/MM/DD/data.txt`.

        Args:
            file_name: The name of the file (e.g., "data.csv" or ".log").
            subdir: The subdirectory within the storage structure (e.g., "raw", "processed").

        Returns:
            The fully constructed PathType for the file.
        """
        if file_name[0] == "." and file_name.count(".") == 1:
            return (
                self.storage_parent_path / subdir / f"{self.storage_folders}{file_name}"
            )
        return self.storage_parent_path / subdir / self.storage_folders / file_name
