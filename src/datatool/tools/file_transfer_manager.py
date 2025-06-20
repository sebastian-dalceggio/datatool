"""
Manages file transfer operations between local and cloud storage.
Provides a unified interface for copying, uploading, and downloading files.
Now refactored to use the Strategy Pattern for extensibility.
"""

from pathlib import Path

from cloudpathlib import CloudPath

from datatool.config import Config
from datatool.types import PathType
from datatool.tools.files import File
from datatool.tools.ssh_path import SshPath
from datatool.tools.transfer_strategies import (
    TransferStrategy,
    LocalToLocalStrategy,
    LocalToCloudStrategy,
    CloudToLocalStrategy,
    CloudToCloudStrategy,
    LocalToSshStrategy,
    SshToLocalStrategy,
    SshToCloudStrategy,
    CloudToSshStrategy,
    SshToSshStrategy,
)


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
        self._strategies: dict[tuple[type, type], TransferStrategy] = {
            (Path, Path): LocalToLocalStrategy(),
            (Path, CloudPath): LocalToCloudStrategy(),
            (CloudPath, Path): CloudToLocalStrategy(),
            (CloudPath, CloudPath): CloudToCloudStrategy(),
            (Path, SshPath): LocalToSshStrategy(),
            (SshPath, Path): SshToLocalStrategy(),
            (SshPath, CloudPath): SshToCloudStrategy(),
            (CloudPath, SshPath): CloudToSshStrategy(),
            (SshPath, SshPath): SshToSshStrategy(),
        }

    def _get_base_path_type(self, path_instance: PathType) -> type:
        """
        Determines the base type for a path instance for strategy lookup.
        This handles subclasses like S3Path mapping to CloudPath.
        """
        if isinstance(path_instance, SshPath):
            return SshPath
        # CloudPath must be checked before Path, as CloudPath is a subclass of Path
        if isinstance(path_instance, CloudPath):
            return CloudPath
        if isinstance(path_instance, Path):
            return Path
        # Fallback for unknown types
        return type(path_instance)

    def transfer_file(
        self, source_file: File, target_file: File, delete_source: bool = False
    ) -> None:
        """
        Transfers a file from a source to a target, optionally deleting the source.
        This method now uses a strategy pattern to dispatch to the correct transfer
        logic based on the source and target path types.

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

        # Ensure target parent directory exists for local paths.
        # SshPath.write_bytes already handles directory creation.
        if isinstance(target_path, Path):
            target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            source_base_type = self._get_base_path_type(source_path)
            target_base_type = self._get_base_path_type(target_path)

            strategy = self._strategies.get((source_base_type, target_base_type))
            if strategy:
                strategy.transfer(source_path, target_path)
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
