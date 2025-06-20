"""Module for handling SSH/SFTP path abstractions."""

import atexit
import stat
import weakref
from functools import lru_cache
from pathlib import PurePosixPath
from urllib.parse import urlparse

import paramiko


# Keep a weak set of clients to close them at exit, without preventing garbage collection.
_active_clients: weakref.WeakSet[paramiko.SSHClient] = weakref.WeakSet()


def _close_all_ssh_clients():
    """Close all cached SSH clients on exit."""
    # Iterate over a copy as the set may change during iteration
    for client in list(_active_clients):
        # Check if transport is still active before trying to close
        if client.get_transport() and client.get_transport().is_active():
            client.close()


atexit.register(_close_all_ssh_clients)


@lru_cache(maxsize=32)
def get_ssh_client(
    hostname: str,
    port: int,
    username: str | None,
    password: str | None = None,
    key_filename: str | None = None,
) -> paramiko.SSHClient:
    """
    Creates and caches a paramiko.SSHClient for a given connection.
    Authentication is attempted using the provided credentials,
    then user's default SSH keys, and SSH agent.
    """
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=hostname,
        port=port,
        username=username,
        password=password,
        key_filename=key_filename,
    )
    _active_clients.add(client)
    return client


class SshPath:
    """
    A class to represent and interact with files over SSH using paramiko.
    This class mimics a subset of the pathlib.Path interface.

    An SshPath is initialized with a URL, e.g., "ssh://user@host:port/path/to/file".
    """

    def __init__(
        self, url: str, password: str | None = None, private_key_path: str | None = None
    ):
        parsed_url = urlparse(url)
        if parsed_url.scheme != "ssh":
            raise ValueError(f"Invalid SSH URL scheme: {parsed_url.scheme}")

        self.hostname: str = parsed_url.hostname or ""
        self.port: int = parsed_url.port or 22
        self.username: str | None = parsed_url.username or None
        self.path: str = parsed_url.path

        if not self.hostname:
            raise ValueError("Hostname is required for SSH path")

        # Store authentication details for propagation in child paths.
        self._password = password
        self._private_key_path = private_key_path

        # Defer client creation until it's needed.
        self._client: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    @property
    def client(self) -> paramiko.SSHClient:
        """Lazy-loads and caches the SSH client."""
        if self._client is None or not (
            (transport := self._client.get_transport()) and transport.is_active()
        ):
            self._client = get_ssh_client(
                self.hostname,
                self.port,
                self.username,
                self._password,
                self._private_key_path,
            )
        return self._client

    @property
    def sftp(self) -> paramiko.SFTPClient:
        """Lazy-loads an SFTP client from the SSH connection."""
        if self._sftp is None or self._sftp.sock.closed:
            self._sftp = self.client.open_sftp()
        return self._sftp

    @property
    def parent(self) -> "SshPath":
        """Returns a new SshPath for the parent directory."""
        # Propagate authentication details to the new SshPath instance.
        parent_path = str(PurePosixPath(self.path).parent)
        # Reconstruct the URL for the parent path.
        parent_url = (
            f"ssh://{self.username or ''}@{self.hostname}:{self.port}{parent_path}"
        )
        return SshPath(
            parent_url, password=self._password, private_key_path=self._private_key_path
        )

    @property
    def name(self) -> str:
        """The name of the file or directory."""
        return str(PurePosixPath(self.path).name)

    def is_absolute(self) -> bool:
        """SshPath is always considered absolute."""
        return True

    def exists(self) -> bool:
        """Check if the remote path exists."""
        try:
            self.sftp.stat(self.path)
            return True
        except FileNotFoundError:
            return False

    def is_dir(self) -> bool:
        """Check if the remote path is a directory."""
        try:
            s = self.sftp.stat(self.path)
            # The st_mode attribute on SFTPAttributes can also be None, so we must check.
            if s and s.st_mode is not None:
                return stat.S_ISDIR(s.st_mode)
            return False
        except FileNotFoundError:
            return False

    def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory. Corresponds to `path.parent.mkdir()`."""
        if not parents:
            self.sftp.mkdir(self.path)
            return

        # Implement mkdir -p logic
        parts = self.path.strip("/").split("/")
        current_path = ""
        for part in parts:
            if not part:
                continue
            current_path = f"{current_path}/{part}"
            try:
                self.sftp.stat(current_path)
            except FileNotFoundError:
                self.sftp.mkdir(current_path)

    def read_bytes(self) -> bytes:
        """Read the content of the remote file as bytes."""
        with self.sftp.open(self.path, "rb") as f:
            return f.read()

    def write_bytes(self, data: bytes) -> None:
        """Write bytes to the remote file."""
        self.mkdir(parents=True, exist_ok=True)  # Ensure parent directories exist
        with self.sftp.open(self.path, "wb") as f:
            f.write(data)

    def read_text(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """
        Read the content of the remote file as text.

        Args:
            encoding: The encoding to use for decoding the file. Defaults to "utf-8".
            errors: The error handling scheme to use for decoding errors.

        Returns:
            The decoded string content of the file.
        """
        return self.read_bytes().decode(encoding, errors)

    def write_text(
        self, data: str, encoding: str = "utf-8", errors: str = "strict"
    ) -> None:
        """
        Write text to the remote file.

        Args:
            data: The string data to write.
            encoding: The encoding to use for encoding the data. Defaults to "utf-8".
            errors: The error handling scheme to use for encoding errors.
        """
        self.write_bytes(data.encode(encoding, errors))

    def unlink(self, missing_ok: bool = False) -> None:
        """Remove the remote file."""
        try:
            self.sftp.remove(self.path)
        except FileNotFoundError:
            if not missing_ok:
                raise

    def __str__(self) -> str:
        user_part = f"{self.username}@" if self.username else ""
        return f"ssh://{user_part}{self.hostname}:{self.port}{self.path}"  # type: ignore[return-value]

    def __repr__(self) -> str:
        # Omit sensitive info like password from repr
        user_part = f"{self.username}@" if self.username else ""
        auth_info = ""
        if self._private_key_path:
            auth_info += f", private_key_path='{self._private_key_path}'"
        # Do not include password in repr
        return f"SshPath('ssh://{user_part}{self.hostname}:{self.port}{self.path}'{auth_info})"

    def __truediv__(self, other: str) -> "SshPath":
        """Allows joining paths with the / operator."""
        new_path = str(PurePosixPath(self.path) / other)
        new_url = f"ssh://{self.username or ''}@{self.hostname}:{self.port}{new_path}"
        return SshPath(
            new_url, password=self._password, private_key_path=self._private_key_path
        )
