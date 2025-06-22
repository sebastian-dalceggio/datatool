"""
Custom type aliases used throughout the datatool package.
"""

from pathlib import Path

from cloudpathlib import CloudPath

from datatool.paths.ssh_path import SshPath


PathType = Path | CloudPath | SshPath
