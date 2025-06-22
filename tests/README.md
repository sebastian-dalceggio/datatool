# DataTool Tests

This directory contains the unit and integration tests for the `datatool` package. The tests are written using `pytest` and aim to ensure the correctness and reliability of the library's functionalities across various scenarios, including local and cloud file operations.

## Test Cases

Below is a list of the primary test cases organized by the modules they cover:

### `tests/tools/test_files.py`
-   `test_file_initialize_path_logic`: Tests the internal path initialization logic.
-   `test_file_initialization_relative_path_str`: Verifies `File` initialization with a relative string path.
-   `test_file_initialization_relative_pathtype`: Verifies `File` initialization with a relative `Path` object.
-   `test_file_initialization_absolute_path_str`: Verifies `File` initialization with an absolute string path (local, cloud, or SSH).
-   `test_file_initialization_absolute_pathtype`: Verifies `File` initialization with an absolute `Path` object (local, cloud, or SSH).
-   `test_file_save`: Tests the `save` method for `File` objects, including content handling and directory creation.
-   `test_file_save_no_content_error`: Ensures `save` raises an error when no content is available.
-   `test_file_read`: Tests the `read` method for `File` objects, including content caching.
-   `test_file_clear_content`: Verifies the `clear_content` method correctly clears cached data.
-   `test_textfile_save_and_read`: Tests the `_save` and `_read` implementations specific to `TextFile`.
-   `test_textfile_default_encoding`: Confirms `TextFile` uses UTF-8 as its default encoding.

### `tests/files/test_file_transfer_manager.py`

-   `test_transfer_file_dispatches_correctly`: Tests that `FileTransferManager` dispatches to the correct strategy based on source and target path types (local, cloud, SSH).
-   `test_transfer_file_with_delete_source`: Verifies that the source file is deleted after transfer when specified.
-   `test_transfer_file_unsupported_types`: Checks that `TypeError` is raised for unsupported path type combinations during transfer.
-   `test_transfer_file_exception_handling`: Ensures exceptions from underlying file operations are propagated and logged.
-   `test_local_to_local_strategy`: Tests the `LocalToLocalStrategy` for copying local files.
-   `test_local_to_cloud_strategy`: Tests the `LocalToCloudStrategy` for uploading local files to cloud storage.
-   `test_cloud_to_local_strategy`: Tests the `CloudToLocalStrategy` for downloading cloud objects to local files.
-   `test_cloud_to_cloud_strategy`: Tests the `CloudToCloudStrategy` for copying objects between cloud storage providers.
-   `test_local_to_ssh_strategy`: Tests the `LocalToSshStrategy` for uploading local files to an SSH server.
-   `test_ssh_to_local_strategy`: Tests the `SshToLocalStrategy` for downloading files from an SSH server to local.
-   `test_ssh_to_cloud_strategy`: Tests the `SshToCloudStrategy` for transferring files from an SSH server to cloud storage.
-   `test_cloud_to_ssh_strategy`: Tests the `CloudToSshStrategy` for transferring files from cloud storage to an SSH server.
-   `test_ssh_to_ssh_strategy`: Tests the `SshToSshStrategy` for transferring files between two SSH servers.

### `tests/paths/test_paths.py`

-   `test_get_path_from_str_local`: Tests `get_path_from_str` for local file paths.
-   `test_get_path_from_str_cloud`: Tests `get_path_from_str` for various cloud file paths (S3, GS, Azure Blob).
-   `test_get_path_from_str_empty`: Tests `get_path_from_str` with an empty string input.

### `tests/paths/test_ssh_path.py`

-   `test_ssh_path_initialization`: Tests `SshPath` object creation with various URL formats.
-   `test_ssh_path_client_and_sftp_lazy_loading`: Verifies lazy loading and caching of SSH and SFTP clients.
-   `test_ssh_path_parent_and_name`: Tests the `parent` and `name` properties for correct path manipulation.
-   `test_ssh_path_is_absolute`: Confirms `SshPath` instances are always considered absolute.
-   `test_ssh_path_exists`: Checks if the `exists` method correctly determines the presence of a remote path.
-   `test_ssh_path_is_dir`: Verifies the `is_dir` method accurately identifies remote directories.
-   `test_ssh_path_mkdir`: Tests the `mkdir` method, including parent directory creation logic.
-   `test_ssh_path_read_write_bytes`: Tests reading and writing binary data to remote SSH files.
-   `test_ssh_path_read_write_text`: Tests reading and writing text data to remote SSH files with specified encoding.
-   `test_ssh_path_unlink`: Verifies the `unlink` method correctly removes remote files.
-   `test_ssh_path_truediv`: Tests the `/` operator for joining SSH paths.
-   `test_ssh_path_str_and_repr`: Confirms the string and representation methods provide correct and safe output.

### `tests/test_config.py`

-   `test_config_initialization_defaults`: Verifies `Config` initialization with default values.
-   `test_config_initialization_custom_values`: Verifies `Config` initialization with custom values.
-   `test_config_datetime_string_parsing`: Tests `Config`'s datetime parsing from a string.
-   `test_config_type_errors`: Ensures `Config` raises `TypeError` for invalid input types during initialization.
-   `test_get_file_storage_path`: Tests the `get_file_storage_path` method for standard file names.
-   `test_get_file_storage_path_special_dotfile`: Tests `get_file_storage_path` for special dotfiles (e.g., `.log`).

### `tests/utils/test_datetime.py`

-   `test_get_datetime_from_str_valid`: Tests `get_datetime_from_str` with valid input.
-   `test_get_datetime_from_str_invalid_format`: Tests `get_datetime_from_str` with an invalid format string for the input.

### `tests/utils/test_logger.py`

-   `test_get_logger_with_file`: Test `get_logger` with a file handler.
-   `test_get_logger_with_stream`: Test `get_logger` with a stream handler.
-   `test_get_logger_with_file_and_stream`: Test `get_logger` with both file and stream handlers.
-   `test_get_logger_no_handler_error`: Test `get_logger` raises `ValueError` if no handlers are configured and none provided.