# DataTool

DataTool is a Python library designed to simplify and unify file operations across different storage backends, including local filesystems, cloud storage, and SSH/SFTP servers. It provides a consistent, high-level API for managing and transferring files, abstracting away the complexities of underlying protocols.

## Key Features

The core of DataTool revolves around a few key abstractions:

*   **Unified Path Objects**: Handles local paths (`pathlib.Path`), cloud paths (`cloudpathlib.CloudPath`), and SSH paths (`SshPath`) through a consistent interface. The `get_path_from_str` utility automatically determines the correct path type from a string URI.

*   **File Abstraction (`File`, `TextFile`)**: Provides a generic way to interact with files regardless of their location. It supports reading, writing, and in-memory content caching.
*   **File Abstraction (`File`, `TextFile`, `BytesFile`, `JsonFile`)**: Provides a generic way to interact with files regardless of their location. It supports reading, writing, and in-memory content caching.
*   **Web Scraping and Content Download (`DownloadProcess`)**: Integrates with Playwright to enable advanced web interaction, including:
    *   **HTML Capture**: Save the full HTML content of visited pages.
    *   **File Downloads**: Automatically capture and save files triggered by page navigation.
    *   **API Response Interception**: Intercept and save specific API responses (e.g., JSON data) based on URL patterns.
    *   **Proxy Support**: Configure proxy settings for web requests.
    *   **Headless/Headed Browsing**: Control browser visibility during operations.

*   **Flexible File Transfers (`FileTransferManager`)**: A powerful manager that uses a strategy pattern to transfer files between any supported storage types. This allows for seamless operations like:
    *   Local to Local
    *   Local to Cloud (S3, GCS, Azure Blob)
    *   Cloud to Local
    *   Cloud to Cloud (cross-provider)
    *   Local to SSH
    *   SSH to Local
    *   Cloud to SSH
    *   SSH to Cloud
    *   SSH to SSH

*   **Centralized Configuration (`Config`)**: Manages settings such as storage paths, logging, and date-based folder structures, providing a single source of truth for file operations.

## Supported Actions

DataTool supports a wide range of file manipulation and transfer actions:

*   **Path Resolution**: Convert string paths (e.g., `/path/to/file`, `s3://bucket/key`, `ssh://user@host/path`) into appropriate `Path`-like objects.
*   **File I/O**: Read and write content to and from local, cloud, or SSH locations with automatic caching.
*   **File Transfer**: Copy files between any two locations (local, cloud, SSH) with a single `transfer_file` call, leveraging a strategy pattern for efficient and type-aware transfers.
*   **Source Deletion**: Optionally delete the source file after a successful transfer.
*   **Directory Management**: Automatically create parent directories for local file writes.

This combination of features makes DataTool an effective utility for building data pipelines and workflows that involve multiple storage systems.

## When is `datatool` useful?

This package is particularly well-suited for projects that:

-   **Require multi-storage support:** If your application needs to interact seamlessly with both local file systems and various cloud storage providers (e.g., S3, Google Cloud Storage, Azure Blob Storage) without rewriting file I/O logic for each.
-   **Benefit from abstracted file handling:** When you want to treat files as objects with content and paths, abstracting away the specifics of `pathlib` or `cloudpathlib` for common operations like reading, writing, and path resolution.
-   **Need unified file transfer:** For scenarios where you frequently transfer files between different storage locations (local-to-local, local-to-cloud, cloud-to-local, cloud-to-cloud) and desire a single, consistent API for these operations.
-   **Value centralized configuration:** If your project can benefit from a central `Config` object to manage settings, logging, and file storage paths, ensuring consistency across different modules.
-   **Prioritize code clarity and maintainability:** By providing a higher-level abstraction, `datatool` can make your file-related code cleaner, more readable, and easier to maintain, especially in data-intensive applications.

## When `datatool` might not be adequate?

While `datatool` offers significant advantages in many scenarios, it might not be the optimal choice for:

-   **Extremely performance-critical operations:** The abstraction layers, while convenient, introduce a minor overhead compared to direct, low-level `pathlib` or `cloudpathlib` API calls. For applications where every microsecond counts in file I/O, direct manipulation might be preferred.
-   **Highly specialized file formats or operations:** If your project requires very granular, low-level control over specific file formats (e.g., custom binary parsing, highly optimized streaming), the generic `File` abstraction might be too high-level. While `File` can be subclassed, direct implementation might be simpler for truly unique requirements.
-   **Minimalist projects with no remote storage needs:** For very small scripts or utilities that exclusively interact with local files and have no foreseeable need for cloud integration, the setup and overhead of `datatool`'s abstractions might be unnecessary.
-   **Projects with existing, deeply integrated file management systems:** If your codebase already has a mature, complex, and highly customized file management infrastructure, integrating `datatool` might lead to redundancy or unnecessary refactoring.
-   **Direct `pathlib` or `cloudpathlib` feature reliance:** If your workflow heavily depends on specific, advanced features or direct object manipulation provided solely by `pathlib` or `cloudpathlib` that are not exposed or abstracted by `datatool`.

In summary, `datatool` is designed to streamline common data handling tasks, particularly those involving diverse storage backends. Evaluate its fit based on your project's scale, performance requirements, and the complexity of your file interaction patterns.
