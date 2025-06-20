"""Tests for the datatool.tools.file_transfer_manager module."""

from pathlib import Path

import pytest
from cloudpathlib import CloudPath, S3Path, GSPath
from pytest_mock.plugin import MockerFixture, MockType

from datatool.config import Config
from datatool.tools.files import File
from datatool.tools.file_transfer_manager import FileTransferManager


@pytest.fixture
def mock_file_obj(mocker: MockerFixture) -> MockType:
    """Fixture to create a mock File object."""
    mock = mocker.MagicMock(spec=File)
    mock.name = "test_file.txt"
    mock.path = None  # To be set in tests
    mock.clear_content = mocker.MagicMock()
    return mock


@pytest.fixture
def transfer_manager(mock_config: Config) -> FileTransferManager:
    """Fixture for FileTransferManager instance."""
    return FileTransferManager(config=mock_config)


def test_transfer_local_to_local(
    transfer_manager: FileTransferManager,
    mock_file_obj: MockType,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """Test transferring a file from local to local."""
    mock_shutil_copy = mocker.patch("shutil.copy")
    source_path = tmp_path / "source.txt"
    source_path.touch()
    target_path = (
        tmp_path / "target_dir" / "target.txt"
    )  # target_dir does not exist yet

    source_file = mock_file_obj
    source_file.path = source_path
    target_file = mocker.MagicMock(spec=File)
    target_file.name = "target.txt"
    target_file.path = target_path

    transfer_manager.transfer_file(source_file, target_file)

    assert target_path.parent.exists()  # Check parent dir creation
    mock_shutil_copy.assert_called_once_with(source_path, target_path)
    source_file.clear_content.assert_not_called()  # delete_source is False by default


def test_transfer_local_to_cloud(
    transfer_manager: FileTransferManager,
    mock_file_obj: MockType,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """Test transferring a file from local to cloud."""
    mock_upload_from = mocker.patch.object(CloudPath, "upload_from")
    source_path = tmp_path / "source.txt"
    source_path.touch()
    target_path = S3Path("s3://my-bucket/target.txt")

    source_file = mock_file_obj
    source_file.path = source_path
    target_file = mocker.MagicMock(spec=File)
    target_file.name = "target.txt"
    target_file.path = target_path

    transfer_manager.transfer_file(source_file, target_file)
    mock_upload_from.assert_called_once_with(source_path)


def test_transfer_cloud_to_local(
    transfer_manager: FileTransferManager,
    mock_file_obj: MockType,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """Test transferring a file from cloud to local."""
    mock_download_to = mocker.patch.object(CloudPath, "download_to")
    source_path = GSPath("gs://my-bucket/source.txt")
    target_path = tmp_path / "local_target_dir" / "target.txt"

    source_file = mock_file_obj
    source_file.path = source_path
    target_file = mocker.MagicMock(spec=File)
    target_file.name = "target.txt"
    target_file.path = target_path

    transfer_manager.transfer_file(source_file, target_file)

    assert target_path.parent.exists()
    mock_download_to.assert_called_once_with(target_path)


def test_transfer_cloud_to_cloud(
    transfer_manager: FileTransferManager,
    mock_file_obj: MockType,
    mocker: MockerFixture,
):
    """Test transferring a file from cloud to cloud."""
    mock_cloud_copy = mocker.patch.object(CloudPath, "copy")
    source_path = S3Path("s3://source-bucket/source.txt")
    target_path = GSPath("gs://target-bucket/target.txt")

    source_file = mock_file_obj
    source_file.path = source_path
    target_file = mocker.MagicMock(spec=File)
    target_file.name = "target.txt"
    target_file.path = target_path

    transfer_manager.transfer_file(source_file, target_file)
    mock_cloud_copy.assert_called_once_with(target_path)


def test_transfer_file_with_delete_source(
    transfer_manager: FileTransferManager,
    mock_file_obj: MockType,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """Test transferring a file and deleting the source."""
    mock_shutil_copy = mocker.patch("shutil.copy")
    mock_unlink = mocker.patch.object(Path, "unlink")

    source_path = tmp_path / "source_to_delete.txt"
    source_path.touch()  # Needs to exist for unlink
    target_path = tmp_path / "target_after_delete.txt"

    source_file = mock_file_obj
    source_file.path = source_path
    target_file = mocker.MagicMock(spec=File)
    target_file.name = "target.txt"
    target_file.path = target_path

    transfer_manager.transfer_file(source_file, target_file, delete_source=True)

    mock_shutil_copy.assert_called_once_with(source_path, target_path)
    mock_unlink.assert_called_once()
    source_file.clear_content.assert_called_once()


def test_transfer_file_unsupported_types(
    transfer_manager: FileTransferManager, mocker: MockerFixture
):
    """Test transfer_file raises TypeError for unsupported path type combinations."""
    source_file = mocker.MagicMock(spec=File)
    source_file.name = "source"
    source_file.path = object()  # An unsupported type

    target_file = mocker.MagicMock(spec=File)
    target_file.name = "target"
    target_file.path = Path("/tmp/target")

    with pytest.raises(TypeError, match="Unsupported path types for transfer:"):
        transfer_manager.transfer_file(source_file, target_file)


def test_transfer_file_exception_handling(
    transfer_manager: FileTransferManager,
    mock_file_obj: MockType,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """Test that exceptions from underlying operations are propagated and logged."""
    mocker.patch("shutil.copy", side_effect=OSError("Disk full"))
    source_path = tmp_path / "source.txt"
    target_path = tmp_path / "target.txt"

    source_file = mock_file_obj
    source_file.path = source_path
    target_file = mocker.MagicMock(spec=File)
    target_file.name = "target.txt"
    target_file.path = target_path

    with pytest.raises(OSError, match="Disk full"):
        transfer_manager.transfer_file(source_file, target_file)
