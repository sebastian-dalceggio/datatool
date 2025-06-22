"""Tests for the datatool.files.file_transfer_manager and transfer_strategies modules."""

from pathlib import Path
import logging
from typing import cast

import pytest
from cloudpathlib import CloudPath, S3Path, GSPath
from pytest_mock.plugin import MockerFixture, MockType

from datatool.config import Config
from datatool.files.files import File
from datatool.files.file_transfer_manager import FileTransferManager
from datatool.paths.ssh_path import SshPath
from datatool.files.transfer_strategies import (
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


@pytest.fixture
def mock_config(mocker: MockerFixture) -> Config:
    """Fixture for a mocked Config object with a mocked logger."""
    mock_config_instance = mocker.Mock(spec=Config)
    # Mock the logger attribute
    mock_logger = mocker.Mock(spec=logging.Logger)
    # Ensure logger methods are also mocks
    mock_logger.info = mocker.Mock()
    mock_logger.error = mocker.Mock()
    mock_config_instance.logger = mock_logger
    # Mock other attributes that might be accessed by FileTransferManager or Config methods
    mock_config_instance.storage_parent_path = mocker.Mock(spec=Path)
    mock_config_instance.storage_parent_path.mkdir = mocker.Mock()
    mock_config_instance.storage_folders = "YYYY/MM/DD"  # Example value
    return mock_config_instance


@pytest.fixture
def transfer_manager(mock_config: Config, mocker: MockerFixture) -> FileTransferManager:
    """Fixture for FileTransferManager instance, with strategies mocked."""
    manager = FileTransferManager(config=mock_config)
    # Mock all strategy instances to control their behavior in tests
    manager._strategies = {
        (Path, Path): mocker.Mock(spec=LocalToLocalStrategy),
        (Path, CloudPath): mocker.Mock(spec=LocalToCloudStrategy),
        (CloudPath, Path): mocker.Mock(spec=CloudToLocalStrategy),
        (CloudPath, CloudPath): mocker.Mock(spec=CloudToCloudStrategy),
        (Path, SshPath): mocker.Mock(spec=LocalToSshStrategy),
        (SshPath, Path): mocker.Mock(spec=SshToLocalStrategy),
        (SshPath, CloudPath): mocker.Mock(spec=SshToCloudStrategy),
        (CloudPath, SshPath): mocker.Mock(spec=CloudToSshStrategy),
        (SshPath, SshPath): mocker.Mock(spec=SshToSshStrategy),
    }
    return manager


### Tests for FileTransferManager (Strategy Dispatch) ###


@pytest.mark.parametrize(
    "source_path_type, target_path_type, source_path_instance, target_path_instance, expected_strategy_type",
    [
        (Path, Path, Path("source.txt"), Path("target.txt"), LocalToLocalStrategy),
        (
            Path,
            CloudPath,
            Path("source.txt"),
            S3Path("s3://bucket/target.txt"),
            LocalToCloudStrategy,
        ),
        (
            CloudPath,
            Path,
            S3Path("s3://bucket/source.txt"),
            Path("target.txt"),
            CloudToLocalStrategy,
        ),
        (
            CloudPath,
            CloudPath,
            S3Path("s3://bucket/source.txt"),
            GSPath("gs://bucket/target.txt"),
            CloudToCloudStrategy,
        ),
        (
            Path,
            SshPath,
            Path("source.txt"),
            SshPath("ssh://host/target.txt"),
            LocalToSshStrategy,
        ),
        (
            SshPath,
            Path,
            SshPath("ssh://host/source.txt"),
            Path("target.txt"),
            SshToLocalStrategy,
        ),
        (
            SshPath,
            CloudPath,
            SshPath("ssh://host/source.txt"),
            S3Path("s3://bucket/target.txt"),
            SshToCloudStrategy,
        ),
        (
            CloudPath,
            SshPath,
            S3Path("s3://bucket/source.txt"),
            SshPath("ssh://host/target.txt"),
            CloudToSshStrategy,
        ),
        (
            SshPath,
            SshPath,
            SshPath("ssh://host/source.txt"),
            SshPath("ssh://host/target.txt"),
            SshToSshStrategy,
        ),
    ],
)
def test_transfer_file_dispatches_correctly(
    transfer_manager: FileTransferManager,
    mocker: MockerFixture,
    source_path_type: type,
    target_path_type: type,
    source_path_instance: Path | CloudPath | SshPath,
    target_path_instance: Path | CloudPath | SshPath,
    expected_strategy_type: type[TransferStrategy],
):
    """Test that transfer_file dispatches to the correct strategy based on path types."""
    source_file = cast(File, mocker.Mock(spec=File))
    source_file.path = source_path_instance
    source_file.name = "source_file"

    target_file = cast(File, mocker.Mock(spec=File))
    target_file.path = target_path_instance
    target_file.name = "target_file"

    # Mock class methods on pathlib.Path correctly using patch.object
    mock_mkdir: MockType = mocker.patch.object(Path, "mkdir")

    transfer_manager.transfer_file(source_file, target_file)

    # Assert the correct strategy's transfer method was called
    strategy_mock = transfer_manager._strategies.get(
        (source_path_type, target_path_type)
    )
    assert strategy_mock is not None
    cast(MockType, strategy_mock.transfer).assert_called_once_with(
        source_path_instance, target_path_instance
    )

    # Assert mkdir was called for local target paths
    if isinstance(target_path_instance, Path):
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


@pytest.mark.parametrize(
    "path_instance, expected_base_type",
    [
        (Path("/tmp/file.txt"), Path),
        (
            S3Path("s3://bucket/file.txt"),
            CloudPath,
        ),  # S3Path is a subclass of CloudPath
        (
            GSPath("gs://bucket/file.txt"),
            CloudPath,
        ),  # GSPath is a subclass of CloudPath
        (SshPath("ssh://host/file.txt"), SshPath),
    ],
)
def test_get_base_path_type(
    transfer_manager: FileTransferManager,
    path_instance: Path | CloudPath | SshPath,
    expected_base_type: type,
):
    """Test the _get_base_path_type method to ensure correct base type resolution."""
    # Create a dummy config and manager for this test if not using the fixture
    # For this test, we can directly call the private method.
    resolved_type = transfer_manager._get_base_path_type(path_instance)
    assert resolved_type == expected_base_type


def test_transfer_file_with_delete_source(
    transfer_manager: FileTransferManager, mocker: MockerFixture, tmp_path: Path
):
    """Test transferring a file and deleting the source."""
    source_path = tmp_path / "source_to_delete.txt"
    source_path.touch()  # Needs to exist for unlink
    target_path = tmp_path / "target_after_delete.txt"

    source_file = cast(File, mocker.Mock(spec=File))
    source_file.path = source_path
    source_file.name = "source_file"

    # Mock unlink on the class using patch.object
    mock_unlink: MockType = mocker.patch.object(Path, "unlink")

    target_file = cast(File, mocker.Mock(spec=File))
    target_file.name = "target.txt"
    target_file.path = target_path

    # Ensure the strategy mock is set for (Path, Path)
    mock_local_to_local_strategy = transfer_manager._strategies[(Path, Path)]

    transfer_manager.transfer_file(source_file, target_file, delete_source=True)

    cast(MockType, mock_local_to_local_strategy.transfer).assert_called_once_with(
        source_path, target_path
    )
    mock_unlink.assert_called_once_with()
    cast(MockType, source_file.clear_content).assert_called_once_with()


def test_transfer_file_unsupported_types(
    transfer_manager: FileTransferManager, mocker: MockerFixture
):
    """Test transfer_file raises TypeError for unsupported path type combinations."""
    source_file = cast(File, mocker.Mock(spec=File))
    source_file.name = "source"
    source_file.path = mocker.Mock()  # An unsupported type

    target_file = cast(File, mocker.Mock(spec=File))
    target_file.name = "target"
    target_file.path = Path("/tmp/target")

    with pytest.raises(TypeError, match="Unsupported path types for transfer:"):
        transfer_manager.transfer_file(source_file, target_file)


def test_transfer_file_exception_handling(
    transfer_manager: FileTransferManager, mocker: MockerFixture, tmp_path: Path
):
    """Test that exceptions from underlying operations are propagated and logged."""
    source_path = tmp_path / "source.txt"
    source_path.touch()
    target_path = tmp_path / "target.txt"

    source_file = cast(File, mocker.Mock(spec=File))
    source_file.path = source_path
    source_file.name = "source_file"

    target_file = cast(File, mocker.Mock(spec=File))
    target_file.name = "target.txt"
    target_file.path = target_path

    # Mock the strategy to raise an exception
    mock_local_to_local_strategy = transfer_manager._strategies[(Path, Path)]
    cast(MockType, mock_local_to_local_strategy.transfer).side_effect = OSError(
        "Disk full"
    )

    with pytest.raises(OSError, match="Disk full"):
        transfer_manager.transfer_file(source_file, target_file)

    cast(MockType, transfer_manager.config.logger.error).assert_called_once()
    assert (
        "Failed to transfer"
        in cast(MockType, transfer_manager.config.logger.error).call_args[0][0]
    )


### Tests for Transfer Strategies ###


def test_local_to_local_strategy(mocker: MockerFixture, tmp_path: Path):
    """Test LocalToLocalStrategy."""
    mock_copy = mocker.patch("shutil.copy")  # shutil is fine to patch directly
    source_path = tmp_path / "source.txt"
    target_path = tmp_path / "target.txt"
    LocalToLocalStrategy().transfer(source_path, target_path)
    mock_copy.assert_called_once_with(source_path, target_path)


def test_local_to_cloud_strategy(mocker: MockerFixture, tmp_path: Path):
    """Test LocalToCloudStrategy."""
    mock_upload_from: MockType = mocker.patch.object(S3Path, "upload_from")
    source_path = tmp_path / "source.txt"
    target_path = S3Path("s3://bucket/target.txt")
    LocalToCloudStrategy().transfer(source_path, target_path)
    mock_upload_from.assert_called_once_with(source_path)


def test_cloud_to_local_strategy(mocker: MockerFixture, tmp_path: Path):
    """Test CloudToLocalStrategy."""
    mock_download_to: MockType = mocker.patch.object(CloudPath, "download_to")
    source_path = S3Path("s3://bucket/source.txt")
    target_path = tmp_path / "target.txt"
    CloudToLocalStrategy().transfer(source_path, target_path)
    mock_download_to.assert_called_once_with(target_path)


def test_cloud_to_cloud_strategy(mocker: MockerFixture):
    """Test CloudToCloudStrategy."""
    mock_copy: MockType = mocker.patch.object(CloudPath, "copy")
    source_path = S3Path("s3://bucket/source.txt")
    target_path = GSPath("gs://bucket/target.txt")
    CloudToCloudStrategy().transfer(source_path, target_path)
    mock_copy.assert_called_once_with(target_path)


def test_local_to_ssh_strategy(mocker: MockerFixture, tmp_path: Path):
    """Test LocalToSshStrategy."""
    mock_read_bytes: MockType = mocker.patch(
        "pathlib.Path.read_bytes", return_value=b"local data"
    )
    source_path = tmp_path / "source.txt"
    mock_ssh_path = mocker.Mock(spec=SshPath)
    mock_ssh_path.write_bytes = mocker.Mock()  # Explicitly mock the method
    LocalToSshStrategy().transfer(source_path, mock_ssh_path)
    mock_read_bytes.assert_called_once()
    cast(MockType, mock_ssh_path.write_bytes).assert_called_once_with(b"local data")


def test_ssh_to_local_strategy(mocker: MockerFixture, tmp_path: Path):
    """Test SshToLocalStrategy."""
    mock_write_bytes: MockType = mocker.patch("pathlib.Path.write_bytes")
    mock_ssh_path = mocker.Mock(spec=SshPath)
    mock_ssh_path.read_bytes.return_value = b"ssh data"
    target_path = tmp_path / "target.txt"

    SshToLocalStrategy().transfer(mock_ssh_path, target_path)
    mock_ssh_path.read_bytes.assert_called_once()
    mock_write_bytes.assert_called_once_with(b"ssh data")


def test_ssh_to_cloud_strategy(mocker: MockerFixture):
    """Test SshToCloudStrategy."""
    mock_ssh_path = mocker.Mock(spec=SshPath)
    mocker.patch.object(mock_ssh_path, "read_bytes", return_value=b"ssh data")
    mock_cloud_path = mocker.Mock(spec=CloudPath)
    mock_cloud_path.write_bytes = mocker.Mock()  # Explicitly mock the method

    SshToCloudStrategy().transfer(mock_ssh_path, mock_cloud_path)
    mock_ssh_path.read_bytes.assert_called_once()
    cast(MockType, mock_cloud_path.write_bytes).assert_called_once_with(b"ssh data")


def test_cloud_to_ssh_strategy(mocker: MockerFixture):
    """Test CloudToSshStrategy."""
    mock_cloud_path = mocker.Mock(spec=CloudPath)
    mocker.patch.object(mock_cloud_path, "read_bytes", return_value=b"cloud data")
    mock_ssh_path = mocker.Mock(spec=SshPath)
    mock_ssh_path.write_bytes = mocker.Mock()  # Explicitly mock the method

    CloudToSshStrategy().transfer(mock_cloud_path, mock_ssh_path)
    mock_cloud_path.read_bytes.assert_called_once()
    cast(MockType, mock_ssh_path.write_bytes).assert_called_once_with(b"cloud data")


def test_ssh_to_ssh_strategy(mocker: MockerFixture):
    """Test SshToSshStrategy."""
    source_ssh_path = mocker.Mock(spec=SshPath)
    mocker.patch.object(source_ssh_path, "read_bytes", return_value=b"ssh to ssh data")
    target_ssh_path = mocker.Mock(spec=SshPath)
    target_ssh_path.write_bytes = mocker.Mock()  # Explicitly mock the method

    SshToSshStrategy().transfer(source_ssh_path, target_ssh_path)
    source_ssh_path.read_bytes.assert_called_once()
