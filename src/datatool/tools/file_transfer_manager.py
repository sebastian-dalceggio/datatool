"""
Manages file transfer operations between local and cloud storage.
Provides a unified interface for copying, uploading, and downloading files.
"""

from pathlib import Path
import shutil

from cloudpathlib import CloudPath

from datatool.config import Config
from datatool.tools.files import File


class FileTransferManager:
    """
    Manages file transfer operations between different storage types.
    It uses a central configuration object for logging and other settings.
    """

    def __init__(self, config: Config):
        """

        Args:
            config: The configuration object to be used for logging and other settings.
        """
        self.config = config

    def _transfer_local_to_local(self, source_path: Path, target_path: Path) -> None:
        """
        Copies a file from a local path to another local path.

        Args:
            source_path: The local path of the source file.
            target_path: The local path for the target file.
        """
        self.config.logger.debug(
            f"Executing local to local copy: {source_path} -> {target_path}"
        )
        shutil.copy(source_path, target_path)

    def _transfer_local_to_cloud(
        self, source_path: Path, target_path: CloudPath
    ) -> None:
        """
        Uploads a local file to a cloud storage location.

        Args:
            source_path: The local path of the source file.
            target_path: The cloud path for the target file.
        """
        self.config.logger.debug(
            f"Executing local to cloud upload: {source_path} -> {target_path}"
        )
        target_path.upload_from(source_path)

    def _transfer_cloud_to_cloud(
        self, source_path: CloudPath, target_path: CloudPath
    ) -> None:
        """
        Copies a file from one cloud storage location to another.

        Args:
            source_path: The cloud path of the source file.
            target_path: The cloud path for the target file.
        """
        self.config.logger.debug(
            f"Executing cloud to cloud copy: {source_path} -> {target_path}"
        )
        source_path.copy(target_path)

    def _transfer_cloud_to_local(
        self, source_path: CloudPath, target_path: Path
    ) -> None:
        """
        Downloads a file from a cloud storage location to a local path.

        Args:
            source_path: The cloud path of the source file.
            target_path: The local path for the target file.
        """
        self.config.logger.debug(
            f"Executing cloud to local download: {source_path} -> {target_path}"
        )
        source_path.download_to(target_path)

    def transfer_file(
        self, source_file: File, target_file: File, delete_source: bool = False
    ) -> None:
        """
        Transfers a file from a source to a target, optionally deleting the source.

        Args:
            source_file: The File object representing the source.
            target_file: The File object representing the target.
            delete_source: Whether to delete the source file after transfer.

        Raises:
            ValueError: If source or target paths are not set in the File objects.
            TypeError: If path types are unsupported or incompatible for direct transfer.
            Exception: Other exceptions from underlying file operations.
        """
        logger = self.config.logger

        logger.info(
            f"Transfering {source_file.name} from {source_file.path} to {target_file.path}."
        )

        source_path = source_file.path
        target_path = target_file.path

        if isinstance(target_path, Path):
            target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if isinstance(source_path, Path) and isinstance(target_path, Path):
                self._transfer_local_to_local(source_path, target_path)
            elif isinstance(source_path, Path) and isinstance(target_path, CloudPath):
                self._transfer_local_to_cloud(source_path, target_path)
            elif isinstance(source_path, CloudPath) and isinstance(target_path, Path):
                self._transfer_cloud_to_local(source_path, target_path)
            elif isinstance(source_path, CloudPath) and isinstance(
                target_path, CloudPath
            ):
                self._transfer_cloud_to_cloud(source_path, target_path)
            else:
                raise TypeError(
                    f"Unsupported path types for transfer: "
                    f"source={type(source_path)}, target={type(target_path)}"
                )

            if delete_source:
                logger.info(f"Deleting {source_file.name} from {source_path}.")
                source_file.path.unlink()
                source_file.clear_content()

            logger.info(
                f"Successfully transferred {source_file.name} to {target_file.path}."
            )

        except Exception as e:
            logger.error(
                f"Failed to transfer {source_file.name} from {source_file.path} to {target_file.path}: {e}"
            )
            raise
