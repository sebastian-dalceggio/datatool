"""Module for file handling abstractions and implementations.

Provides an abstract base class `File` and concrete implementations like `TextFile`.
"""

from typing import Generic, TypeVar
from abc import ABC, abstractmethod

from datatool.types import PathType
from datatool.config import Config
from datatool.tools.paths import get_path_from_str


T = TypeVar("T")


class File(ABC, Generic[T]):
    """Abstract base class for file operations.

    This class provides a common interface for reading, writing, and managing files,
    potentially in cloud storage. It handles path resolution for local and cloud
    storage based on the provided configuration.

    Attributes:
        name (str): The base name of the file.
        config (Config): The configuration object for this file.
        content (T | None): The content of the file, cached in memory.
        subdir (str): The subdirectory where the file is located/to be stored.
        path (PathType): The full path to the file.
    """

    def __init__(
        self,
        config: Config,
        path_or_name: PathType | str,
        content: T | None = None,
        subdir: str = "",
    ):
        """Initializes a File object.

        Args:
            config: The configuration object.
            path_or_name: An absolute path (local or cloud) as a string or PathType,
                or a relative path/filename as a string.
            content: Optional initial content for the file.
            subdir: The subdirectory to use if `path_or_name` is relative.
        """
        self.config = config
        self.content = content
        self.path: PathType
        self._initialize_path(path_or_name, subdir)

    def _initialize_path(self, path_or_name: PathType | str, subdir: str) -> None:
        """Initializes the file path, name, and subdir from __init__.

        If `path_or_name` is an absolute path, it is used directly.
        If it is a relative path or just a filename, it is resolved against
        the storage path defined in the configuration.

        Args:
            path_or_name: The path or name provided during initialization.
            subdir: The subdirectory to use for relative paths.
        """
        path: PathType

        if isinstance(path_or_name, str):
            path = get_path_from_str(path_or_name)
        else:  # It's a PathType
            path = path_or_name

        # An absolute path (local or cloud) is used directly.
        # A relative path is treated as a file name to be placed in storage.
        if path.is_absolute():
            self.path = path
            self.name = path.name
            self.subdir = ""
        else:
            # The string form of a relative Path is the name.
            name = str(path)
            self.path = self.config.get_file_storage_path(name, subdir)
            self.name = name
            self.subdir = subdir

    @abstractmethod
    def _save(self, content: T, path: PathType) -> None:
        """Abstract method to save content to a specific path.

        To be implemented by subclasses for specific file types.

        Args:
            content: The content to save.
            path: The PathType where the content should be saved.
        """

    def save(self, content: T | None = None, clear_content: bool = True) -> None:
        """Saves the file content to its configured path.

        Args:
            content: Optional content to save. If None, uses `self.content`.
            clear_content: If True, clears the cached content after saving.

        Raises:
            ValueError: If no content is available to save (neither `content`
                parameter is provided nor `self.content` is set).
        """
        if content is not None:
            self.content = content
        if self.content is None:
            raise ValueError("Content not set. Provide content or read a file first.")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.config.logger.info(f"Saving {self.name} to {self.path}.")
        self._save(self.content, self.path)
        if clear_content:
            self.clear_content()

    @abstractmethod
    def _read(self, path: PathType) -> T:
        """Abstract method to read content from a specific path.

        To be implemented by subclasses for specific file types.

        Args:
            path: The PathType from which to read the content.

        Returns:
            The content read from the file.
        """
        pass

    def read(self, use_cache: bool = True) -> T:
        """Reads the file content from its path, caching it in memory.

        Args:
            use_cache: If True (default), returns cached content if available.
                If False, forces a re-read from the source path.

        Returns:
            The content of the file.
        """
        if use_cache and self.content is not None:
            self.config.logger.info(f"Returning cached content for {self.name}.")
            return self.content

        self.config.logger.info(f"Reading {self.name} from {self.path}.")
        self.content = self._read(self.path)
        return self.content

    def clear_content(self) -> None:
        """Clears the cached file content from memory."""
        self.config.logger.info(f"Clearing content of {self.name}.")
        self.content = None


class TextFile(File[str]):
    """A concrete implementation of File for handling text files.

    Attributes:
        encoding (str): The character encoding for reading/writing (defaults to "utf-8").
    """

    def __init__(
        self,
        config: Config,
        path_or_name: PathType | str,
        content: str | None = None,
        subdir: str = "",
        encoding: str = "utf-8",
    ) -> None:
        """Initializes a TextFile object.

        Args:
            config: The configuration object.
            path_or_name: An absolute path (local or cloud) as a string or PathType,
                or a relative path/filename as a string.
            content: Optional initial text content for the file.
            subdir: The subdirectory to use if `path_or_name` is relative.
            encoding: The text encoding to use for read/write operations.
        """
        self.encoding = encoding
        super().__init__(
            config=config,
            path_or_name=path_or_name,
            content=content,
            subdir=subdir,
        )

    def _save(self, content: str, path: PathType) -> None:
        """Saves string content to a text file.

        Args:
            content: The string content to save.
            path: The PathType where the content should be saved.
        """
        path.write_text(content, encoding=self.encoding)

    def _read(self, path: PathType) -> str:
        """Reads content from a text file.

        Args:
            path: The PathType from which to read the content.

        Returns:
            The string content read from the file.
        """
        return path.read_text(encoding=self.encoding)
