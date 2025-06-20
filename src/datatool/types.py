"""
Custom type aliases used throughout the datatool package.
"""

from pathlib import Path

from cloudpathlib import CloudPath

PathType = Path | CloudPath
