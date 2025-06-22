"""Module for defining various file transfer strategies."""

from abc import ABC, abstractmethod
from pathlib import Path
import shutil

from cloudpathlib import CloudPath

from datatool.types import PathType
from datatool.paths.ssh_path import SshPath


class TransferStrategy(ABC):
    """Abstract base class for file transfer strategies."""

    @abstractmethod
    def transfer(self, source_path: PathType, target_path: PathType) -> None:
        """
        Abstract method to execute a file transfer.

        Args:
            source_path: The source path of the file.
            target_path: The target path for the file.
        """
        pass


class LocalToLocalStrategy(TransferStrategy):
    """Strategy for transferring files from local to local."""

    def transfer(self, source_path: PathType, target_path: PathType) -> None:
        assert isinstance(source_path, Path)
        assert isinstance(target_path, Path)
        shutil.copy(source_path, target_path)


class LocalToCloudStrategy(TransferStrategy):
    """Strategy for transferring files from local to cloud."""

    def transfer(self, source_path: PathType, target_path: PathType) -> None:
        assert isinstance(source_path, Path)
        assert isinstance(target_path, CloudPath)
        target_path.upload_from(source_path)


class CloudToLocalStrategy(TransferStrategy):
    """Strategy for transferring files from cloud to local."""

    def transfer(self, source_path: PathType, target_path: PathType) -> None:
        assert isinstance(source_path, CloudPath)
        assert isinstance(target_path, Path)
        source_path.download_to(target_path)


class CloudToCloudStrategy(TransferStrategy):
    """Strategy for transferring files from cloud to cloud."""

    def transfer(self, source_path: PathType, target_path: PathType) -> None:
        assert isinstance(source_path, CloudPath)
        assert isinstance(target_path, CloudPath)
        source_path.copy(target_path)


class LocalToSshStrategy(TransferStrategy):
    """Strategy for transferring files from local to SSH."""

    def transfer(self, source_path: PathType, target_path: PathType) -> None:
        assert isinstance(source_path, Path)
        assert isinstance(target_path, SshPath)
        target_path.write_bytes(source_path.read_bytes())


class SshToLocalStrategy(TransferStrategy):
    """Strategy for transferring files from SSH to local."""

    def transfer(self, source_path: PathType, target_path: PathType) -> None:
        assert isinstance(source_path, SshPath)
        assert isinstance(target_path, Path)
        target_path.write_bytes(source_path.read_bytes())


class SshToCloudStrategy(TransferStrategy):
    """Strategy for transferring files from SSH to cloud."""

    def transfer(self, source_path: PathType, target_path: PathType) -> None:
        assert isinstance(source_path, SshPath)
        assert isinstance(target_path, CloudPath)
        target_path.write_bytes(source_path.read_bytes())


class CloudToSshStrategy(TransferStrategy):
    """Strategy for transferring files from cloud to SSH."""

    def transfer(self, source_path: PathType, target_path: PathType) -> None:
        assert isinstance(source_path, CloudPath)
        assert isinstance(target_path, SshPath)
        target_path.write_bytes(source_path.read_bytes())


class SshToSshStrategy(TransferStrategy):
    """Strategy for transferring files from SSH to SSH."""

    def transfer(self, source_path: PathType, target_path: PathType) -> None:
        assert isinstance(source_path, SshPath)
        assert isinstance(target_path, SshPath)
        target_path.write_bytes(source_path.read_bytes())
