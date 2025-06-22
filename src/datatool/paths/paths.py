from pathlib import Path
import re

from cloudpathlib import CloudPath

from datatool.paths.ssh_path import SshPath
from datatool.types import PathType

_CLOUD_PATH_REGEX = re.compile(r"^(s3://|gs://|az://)")


def get_path_from_str(path: str) -> PathType:
    """
    Converts a string to a Path or CloudPath object.

    Args:
        path: The string representation of the path.
              It can be a local path, a cloud path (e.g., "s3://..."), or an
              SSH path (e.g., "ssh://...").

    Returns:
        A Path, CloudPath, or SshPath object. An empty string will be
        converted to a Path object representing the current directory (".").
    """
    if _CLOUD_PATH_REGEX.match(path):
        return CloudPath(path)  # type: ignore[abstract]
    elif path.startswith("ssh://"):
        return SshPath(path)
    return Path(path)
