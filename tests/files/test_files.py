"""Tests for the datatool.files.files module."""

from pathlib import Path

import pytest
from cloudpathlib import S3Path
from pytest_mock.plugin import MockerFixture, MockType

from datatool.config import Config
from datatool.files.files import File, TextFile, BytesFile, JsonFile
from datatool.types import PathType


class ConcreteFile(File[bytes]):
    """A concrete implementation of File for testing."""

    def _save(self, content: bytes, path: PathType) -> None:
        path.write_bytes(content)

    def _read(self, path: PathType) -> bytes:
        return path.read_bytes()


@pytest.fixture
def mock_path_obj(mocker: MockerFixture) -> MockType:
    """Fixture to create a mock Path or CloudPath object."""
    mock = mocker.MagicMock(spec=Path)  # Use Path as a base for common methods
    mock.is_absolute.return_value = True
    mock.name = "mocked_path.dat"
    mock.parent = mocker.MagicMock(spec=Path)
    mock.parent.mkdir = mocker.MagicMock()
    mock.write_text = mocker.MagicMock()
    mock.read_text = mocker.MagicMock(return_value="file content")
    mock.write_bytes = mocker.MagicMock()
    mock.read_bytes = mocker.MagicMock(return_value=b"byte content")
    return mock


def test_file_initialization_relative_path_str(mock_config: Config):
    """Test File initialization with a relative path string (uses config storage path)."""
    file_name = "test.dat"
    subdir = "data"
    f = ConcreteFile(config=mock_config, path_or_name=file_name, subdir=subdir)
    expected_path = mock_config.get_file_storage_path(file_name, subdir)
    assert f.path == expected_path
    assert f.name == file_name
    assert f.config == mock_config
    assert f.subdir == subdir
    assert f.content is None


def test_file_initialization_relative_pathtype(mock_config: Config):
    """Test File initialization with a relative Path object."""
    file_name = "test.dat"
    subdir = "data"
    path_obj = Path(file_name)
    f = ConcreteFile(config=mock_config, path_or_name=path_obj, subdir=subdir)
    expected_path = mock_config.get_file_storage_path(file_name, subdir)
    assert f.path == expected_path
    assert f.name == file_name
    assert f.subdir == subdir


def test_file_initialization_absolute_path_str(mock_config: Config):
    """Test File initialization with an absolute string path."""
    path_name_part = "file_from_path.dat"
    path_str = f"s3://my-bucket/{path_name_part}"

    f = ConcreteFile(config=mock_config, path_or_name=path_str)

    assert isinstance(f.path, S3Path)
    assert str(f.path) == path_str
    assert f.name == path_name_part, "Name should be derived from path"
    assert f.subdir == "", "Subdir should be empty when an absolute path is provided"


def test_file_initialization_absolute_pathtype(mock_config: Config, tmp_path: Path):
    """Test File initialization with an absolute PathType object."""
    path_name_part = "file_from_path.dat"
    path_obj = tmp_path / path_name_part

    f = ConcreteFile(config=mock_config, path_or_name=path_obj)

    assert f.path == path_obj
    assert f.name == path_name_part, "Name should be derived from path"
    assert f.subdir == "", "Subdir should be empty when an absolute path is provided"


def test_file_initialize_path_logic(mock_config: Config):
    """Test the _initialize_path method's logic for absolute vs relative paths."""
    # Test with a relative path_or_name and subdir
    file_name = "relative.txt"
    subdir = "test_subdir"
    f = ConcreteFile(config=mock_config, path_or_name=file_name, subdir=subdir)
    assert f.path == mock_config.get_file_storage_path(file_name, subdir)
    assert f.name == file_name
    assert f.subdir == subdir

    # Test with an absolute PathType, subdir should be ignored and name derived from path
    abs_path = Path("/absolute/path/to/file.txt")
    f = ConcreteFile(config=mock_config, path_or_name=abs_path, subdir="ignored_subdir")
    assert f.path == abs_path
    assert f.name == "file.txt"
    assert f.subdir == ""  # Should be empty for absolute paths


def test_file_save(mock_config: Config, mock_path_obj: MockType):
    """Test the save method."""
    f = ConcreteFile(config=mock_config, path_or_name=mock_path_obj)
    content_to_save = b"sample data"

    # Save with content argument
    f.save(content=content_to_save, clear_content=False)
    mock_path_obj.parent.mkdir.assert_called_with(parents=True, exist_ok=True)
    mock_path_obj.write_bytes.assert_called_with(content_to_save)
    assert f.content == content_to_save  # Not cleared

    # Save with self.content
    f.content = b"other data"
    f.save(clear_content=True)
    mock_path_obj.write_bytes.assert_called_with(b"other data")
    assert f.content is None  # Cleared


def test_file_save_no_content_error(mock_config: Config, mock_path_obj: MockType):
    """Test save raises ValueError if no content is available."""
    f = ConcreteFile(config=mock_config, path_or_name=mock_path_obj)
    f.content = None
    with pytest.raises(ValueError, match="Content not set."):
        f.save()


def test_file_read(mock_config: Config, mock_path_obj: MockType):
    """Test the read method."""
    f = ConcreteFile(config=mock_config, path_or_name=mock_path_obj)
    f.content = None  # Ensure content is not cached

    # First read
    read_content = f.read()
    mock_path_obj.read_bytes.assert_called_once()
    assert read_content == b"byte content"
    assert f.content == b"byte content"  # Content is cached

    # Second read (should use cached content)
    mock_path_obj.read_bytes.reset_mock()
    read_content_cached = f.read()
    mock_path_obj.read_bytes.assert_not_called()
    assert read_content_cached == b"byte content"


def test_file_clear_content(mock_config: Config, mock_path_obj: MockType):
    """Test the clear_content method."""
    f = ConcreteFile(config=mock_config, path_or_name=mock_path_obj)
    f.content = b"some data"
    f.clear_content()
    assert f.content is None


def test_textfile_save_and_read(
    mock_config: Config, mock_path_obj: MockType, mocker: MockerFixture
):
    """Test TextFile's _save and _read implementations."""
    encoding = "utf-16"
    text_f = TextFile(config=mock_config, path_or_name=mock_path_obj, encoding=encoding)

    # Test _save
    content_to_save = "hello world"
    text_f._save(content_to_save, mock_path_obj)
    mock_path_obj.write_text.assert_called_once_with(content_to_save, encoding=encoding)

    # Test _read
    mock_path_obj.read_text = mocker.MagicMock(
        return_value="你好世界"
    )  # Simulate reading different content
    read_content = text_f._read(mock_path_obj)
    mock_path_obj.read_text.assert_called_once_with(encoding=encoding)
    assert read_content == "你好世界"


def test_textfile_default_encoding(mock_config: Config, mock_path_obj: MockType):
    """Test TextFile uses utf-8 as default encoding."""
    text_f = TextFile(config=mock_config, path_or_name=mock_path_obj)
    assert text_f.encoding == "utf-8"

    content_to_save = "default encoding test"
    text_f._save(content_to_save, mock_path_obj)
    mock_path_obj.write_text.assert_called_once_with(content_to_save, encoding="utf-8")

    text_f._read(mock_path_obj)
    mock_path_obj.read_text.assert_called_once_with(encoding="utf-8")


def test_bytesfile_save_and_read(mock_config: Config, mock_path_obj: MockType):
    """Test BytesFile's _save and _read implementations."""
    bytes_f = BytesFile(config=mock_config, path_or_name=mock_path_obj)

    # Test _save
    content_to_save = b"binary data"
    bytes_f._save(content_to_save, mock_path_obj)
    mock_path_obj.write_bytes.assert_called_once_with(content_to_save)

    # Test _read
    mock_path_obj.read_bytes.return_value = b"read binary data"
    read_content = bytes_f._read(mock_path_obj)
    mock_path_obj.read_bytes.assert_called_once()
    assert read_content == b"read binary data"


def test_jsonfile_save_and_read(
    mock_config: Config, mock_path_obj: MockType, mocker: MockerFixture
):
    """Test JsonFile's _save and _read implementations."""
    json_f = JsonFile(config=mock_config, path_or_name=mock_path_obj)
    mock_json_dumps = mocker.patch("json.dumps", return_value='{"key": "value"}')
    mock_json_loads = mocker.patch("json.loads", return_value={"key": "value"})

    # Test _save
    content_to_save = {"key": "value"}
    json_f._save(content_to_save, mock_path_obj)
    mock_json_dumps.assert_called_once_with(content_to_save, indent=4)
    mock_path_obj.write_text.assert_called_once_with(
        '{"key": "value"}', encoding="utf-8"
    )

    # Test _read
    mock_path_obj.read_text.return_value = '{"key": "value"}'
    read_content = json_f._read(mock_path_obj)
    mock_path_obj.read_text.assert_called_once()
    mock_json_loads.assert_called_once_with('{"key": "value"}')
    assert read_content == {"key": "value"}


def test_jsonfile_default_encoding(mock_config: Config, mock_path_obj: MockType):
    """Test JsonFile uses utf-8 as default encoding."""
    json_f = JsonFile(config=mock_config, path_or_name=mock_path_obj)
    assert json_f.encoding == "utf-8"
