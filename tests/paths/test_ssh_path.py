"""Tests for the datatool.paths.ssh_path module."""

from typing import cast
import pytest
from pytest_mock import MockerFixture, MockType
import paramiko

from datatool.paths.ssh_path import SshPath, get_ssh_client, _active_clients


@pytest.fixture(autouse=True)
def clear_ssh_client_cache():
    """Clear the SSH client cache before each test."""
    get_ssh_client.cache_clear()
    _active_clients.clear()


@pytest.fixture
def mock_ssh_client(mocker: MockerFixture) -> MockType:
    """Mocks paramiko.SSHClient and its methods."""
    mock_client = mocker.MagicMock(spec=paramiko.SSHClient)
    mock_transport = mocker.MagicMock()
    mock_transport.is_active.return_value = True
    mock_client.get_transport.return_value = mock_transport
    mock_client.open_sftp.return_value = mocker.MagicMock(spec=paramiko.SFTPClient)
    mocker.patch("paramiko.SSHClient", return_value=mock_client)
    mocker.patch("paramiko.AutoAddPolicy", return_value=mocker.MagicMock())
    return mock_client


@pytest.fixture
def mock_sftp_client(mock_ssh_client: MockType, mocker: MockerFixture):
    """Mocks paramiko.SFTPClient and its methods."""
    mock_sftp = mocker.MagicMock(spec=paramiko.SFTPClient)
    mock_sftp.sock = mocker.MagicMock()
    mock_sftp.sock.closed = False
    mock_ssh_client.open_sftp.return_value = mock_sftp
    return mock_sftp


def test_ssh_path_initialization():
    """Test SshPath initialization with various URL formats."""
    path = SshPath("ssh://user@host:2222/path/to/file.txt")
    assert path.hostname == "host"
    assert path.port == 2222
    assert path.username == "user"
    assert path.path == "/path/to/file.txt"

    path = SshPath("ssh://host/path/to/file.txt")
    assert path.username is None
    assert path.port == 22

    with pytest.raises(ValueError, match="Invalid SSH URL scheme"):
        SshPath("http://host/path")

    with pytest.raises(ValueError, match="Hostname is required"):
        SshPath("ssh:///path")


def test_ssh_path_client_and_sftp_lazy_loading(
    mock_ssh_client: MockType, mock_sftp_client: MockType
):
    """Test that SSHClient and SFTPClient are lazy-loaded and cached."""
    path = SshPath("ssh://user@host/path")

    # Access client property - should call get_ssh_client and connect
    client1 = path.client
    mock_ssh_client.connect.assert_called_once_with(
        hostname="host", port=22, username="user", password=None, key_filename=None
    )
    assert client1 == mock_ssh_client

    # Access client again - should return cached instance
    client2 = path.client
    mock_ssh_client.connect.assert_called_once()  # Should not be called again
    assert client2 == client1

    # Access sftp property - should call open_sftp
    sftp1 = path.sftp
    mock_ssh_client.open_sftp.assert_called_once()
    assert sftp1 == mock_sftp_client

    # Access sftp again - should return cached instance
    sftp2 = path.sftp
    mock_ssh_client.open_sftp.assert_called_once()  # Should not be called again
    assert sftp2 == sftp1


def test_ssh_path_parent_and_name():
    """Test parent property and name property."""
    path = SshPath("ssh://user@host/path/to/file.txt")
    assert path.name == "file.txt"

    parent_path = path.parent
    assert isinstance(parent_path, SshPath)
    assert parent_path.path == "/path/to"
    assert parent_path.name == "to"

    root_parent = SshPath("ssh://host/").parent
    assert root_parent.path == "/"


def test_ssh_path_is_absolute():
    """Test is_absolute property."""
    path = SshPath("ssh://host/path")
    assert path.is_absolute() is True


def test_ssh_path_exists(mock_sftp_client: MockType, mocker: MockerFixture):
    """Test exists method."""
    path = SshPath("ssh://host/file.txt")
    mock_sftp_client.stat.return_value = mocker.MagicMock()
    assert path.exists() is True

    mock_sftp_client.stat.side_effect = FileNotFoundError
    assert path.exists() is False


def test_ssh_path_is_dir(mock_sftp_client: MockType, mocker: MockerFixture):
    """Test is_dir method."""
    path = SshPath("ssh://host/dir/")
    mock_stat_result = mocker.MagicMock()
    mock_stat_result.st_mode = 16877  # Example mode for a directory (0o040755)
    mock_sftp_client.stat.return_value = mock_stat_result
    mocker.patch("stat.S_ISDIR", return_value=True)
    assert path.is_dir() is True

    mock_stat_result.st_mode = 33188  # Example mode for a file (0o100644)
    mocker.patch("stat.S_ISDIR", return_value=False)
    assert path.is_dir() is False

    mock_sftp_client.stat.side_effect = FileNotFoundError
    assert path.is_dir() is False


def test_ssh_path_mkdir(mock_sftp_client: MockType):
    """Test mkdir method, including parent directory creation logic."""
    path = SshPath("ssh://host/path/to/new_dir")
    mock_sftp_client.stat.side_effect = FileNotFoundError  # Simulate dir not existing

    path.mkdir()
    mock_sftp_client.mkdir.assert_called_once_with("/path/to/new_dir")

    mock_sftp_client.mkdir.reset_mock()
    mock_sftp_client.stat.side_effect = [
        FileNotFoundError,  # For /path
        FileNotFoundError,  # For /path/to
        FileNotFoundError,  # For /path/to/new_dir
    ]
    path.mkdir(parents=True)
    assert mock_sftp_client.mkdir.call_count == 3
    mock_sftp_client.mkdir.assert_any_call("/path")
    mock_sftp_client.mkdir.assert_any_call("/path/to")
    mock_sftp_client.mkdir.assert_any_call("/path/to/new_dir")


def test_ssh_path_read_write_bytes(mock_sftp_client: MockType, mocker: MockerFixture):
    """Test read_bytes and write_bytes methods."""
    path = SshPath("ssh://host/test_dir/file.bin")
    mock_file_handle = mocker.MagicMock()
    mock_sftp_client.open.return_value.__enter__.return_value = mock_file_handle

    # Test write_bytes
    mock_sftp_client.stat.side_effect = (
        FileNotFoundError  # Simulate parent dir not existing
    )
    path.write_bytes(b"test data")
    mock_sftp_client.mkdir.assert_called_once_with(
        "/test_dir"
    )  # For parent dir creation
    mock_sftp_client.open.assert_called_once_with("/test_dir/file.bin", "wb")
    mock_file_handle.write.assert_called_once_with(b"test data")

    # Test read_bytes
    mock_sftp_client.open.reset_mock()
    mock_file_handle.read.return_value = b"read data"
    content = path.read_bytes()
    mock_sftp_client.open.assert_called_once_with("/test_dir/file.bin", "rb")
    mock_file_handle.read.assert_called_once()
    assert content == b"read data"


def test_ssh_path_read_write_text(mock_sftp_client: MockType, mocker: MockerFixture):
    """Test read_text and write_text methods."""
    path = SshPath("ssh://host/file.txt")
    mocker.patch.object(path, "read_bytes", return_value=b"hello world")
    mock_write_bytes = mocker.patch.object(path, "write_bytes")

    # Test read_text
    content = path.read_text(encoding="utf-8")
    cast(MockType, path.read_bytes).assert_called_once()
    assert content == "hello world"

    # Test write_text
    path.write_text("new data", encoding="utf-8")
    mock_write_bytes.assert_called_once_with(b"new data")


def test_ssh_path_unlink(mock_sftp_client: MockType):
    """Test unlink method."""
    path = SshPath("ssh://host/file.txt")
    path.unlink()
    mock_sftp_client.remove.assert_called_once_with("/file.txt")

    mock_sftp_client.remove.reset_mock()
    mock_sftp_client.remove.side_effect = FileNotFoundError
    path.unlink(missing_ok=True)
    mock_sftp_client.remove.assert_called_once()

    mock_sftp_client.remove.reset_mock()
    with pytest.raises(FileNotFoundError):
        path.unlink(missing_ok=False)


def test_ssh_path_truediv():
    """Test __truediv__ operator."""
    base_path = SshPath("ssh://user@host/base")
    new_path = base_path / "subdir" / "file.txt"
    assert isinstance(new_path, SshPath)
    assert new_path.path == "/base/subdir/file.txt"
    assert new_path.username == "user"
    assert new_path.hostname == "host"


def test_ssh_path_str_and_repr():
    """Test __str__ and __repr__ methods."""
    path = SshPath(
        "ssh://user@host:2222/path/to/file.txt", private_key_path="/tmp/key.pem"
    )
    assert str(path) == "ssh://user@host:2222/path/to/file.txt"
    assert (
        "SshPath('ssh://user@host:2222/path/to/file.txt', private_key_path='/tmp/key.pem')"
        in repr(path)
    )

    path_no_user = SshPath("ssh://host/path")
    assert str(path_no_user) == "ssh://host:22/path"
    assert "SshPath('ssh://host:22/path')" in repr(path_no_user)
