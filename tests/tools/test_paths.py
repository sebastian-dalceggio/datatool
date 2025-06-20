"""Tests for the datatool.tools.paths module."""

from pathlib import Path
import pytest
from cloudpathlib import S3Path, GSPath, AzureBlobPath

from datatool.tools.paths import get_path_from_str


def test_get_path_from_str_local():
    """Test get_path_from_str with a local path string."""
    local_path_str = "/tmp/test_file.txt"
    path_obj = get_path_from_str(local_path_str)
    assert isinstance(path_obj, Path)
    assert str(path_obj) == local_path_str

    relative_path_str = "data/file.csv"
    path_obj_rel = get_path_from_str(relative_path_str)
    assert isinstance(path_obj_rel, Path)
    assert str(path_obj_rel) == relative_path_str


@pytest.mark.parametrize(
    "cloud_path_str, expected_type",
    [
        ("s3://my-bucket/my-folder/file.json", S3Path),
        ("gs://my-gcs-bucket/data/info.txt", GSPath),
        ("az://my-container/path/to/blob.zip", AzureBlobPath),
    ],
)
def test_get_path_from_str_cloud(cloud_path_str, expected_type):
    """Test get_path_from_str with various cloud path strings."""
    path_obj = get_path_from_str(cloud_path_str)
    assert isinstance(path_obj, expected_type)
    assert str(path_obj) == cloud_path_str


def test_get_path_from_str_empty():
    """Test get_path_from_str with an empty string (results in local Path)."""
    path_obj = get_path_from_str("")
    assert isinstance(path_obj, Path)
    assert str(path_obj) == "."
