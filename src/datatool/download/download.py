from dataclasses import dataclass
import os
from typing import List, Literal, Type, cast, Union
from urllib.parse import urlparse
from playwright.sync_api import (
    sync_playwright,
    ProxySettings,
    Browser,
    BrowserContext,
    Playwright,
    Page,
    Response,
    Download,
)
from playwright._impl._errors import Error
from bs4 import BeautifulSoup

from datatool.config import Config
from datatool.files.files import File, BytesFile, TextFile, JsonFile
from datatool.utils.utils import incremental_counter


@dataclass
class DownloadTask:
    """Represents a set of download actions for a single URL visit."""

    # No __doc__ on dataclass attributes, so we document them here.
    #
    # url: The URL to visit.
    # html_file: File object to save the page's HTML content.
    # download_file: File object to save a downloaded file.
    # capture_api_urls: A list of URL substrings to intercept API responses from.
    # capture_api_file_type: The type of file to save captured API responses.
    # capture_api_subdir: The subdirectory to save captured API responses.
    # capture_api_response_fn: The method to use for getting API response content.

    url: str
    html_file: TextFile | None = None
    download_file: BytesFile | None = None
    capture_api_urls: List[str] | None = None
    capture_api_file_type: Type[File] = JsonFile
    capture_api_subdir: str = ""
    capture_api_response_fn: Literal["text", "json"] = "json"


class Proxy:
    """
    Represents proxy settings for Playwright and the requests library.

    Attributes:
        server (str): The proxy server address (e.g., "host:port").
        protocol (str): The proxy protocol (e.g., "http", "socks5").
        username (str | None): Optional username for proxy authentication.
        password (str | None): Optional password for proxy authentication.
    """

    def __init__(
        self,
        server: str,
        protocol: str = "http",
        username: str | None = None,
        password: str | None = None,
    ):
        """Initializes the Proxy object.

        Args:
            server: The proxy server address (e.g., "host:port").
            protocol: The proxy protocol (e.g., "http", "socks5"). Defaults to "http".
            username: Optional username for proxy authentication.
            password: Optional password for proxy authentication.
        """
        self.server = server
        self.protocol = protocol
        self.username = username
        self.password = password

    def get_playwright_proxy(self) -> ProxySettings:
        """
        Returns proxy settings formatted for Playwright.

        Returns:
            A ProxySettings object for Playwright.
        """
        return ProxySettings(
            {  # type: ignore
                "server": f"{self.protocol}://{self.server}",
                "username": self.username,
                "password": self.password,
            }
        )

    def get_requests_proxy(self) -> dict[str, str]:
        """
        Returns proxy settings formatted for the requests library.

        Returns:
            A dictionary with "http" and "https" proxy URLs.
        """
        if self.username and self.password:
            proxy = f"{self.protocol}://{self.username}:{self.password}@{self.server}"
            proxies = {
                "http": proxy,
                "https": proxy,
            }
        else:
            proxy = f"{self.protocol}://{self.server}"
            proxies = {
                "http": proxy,
                "https": proxy,
            }
        return proxies


class PlaywrightBrowser:
    """
    A context manager for managing a Playwright browser and a single context.

    This class handles the startup and shutdown of Playwright, a browser,
    and a browser context, ensuring that all resources are properly released.

    Attributes:
        headless (bool): Whether to run the browser in headless mode.
        proxy (ProxySettings | None): The proxy settings for Playwright.
        browser (Browser | None): The Playwright Browser instance.
        context (BrowserContext | None): The Playwright BrowserContext instance.
        context_kwargs (dict): Additional keyword arguments for the browser context.

    Usage:
        with PlaywrightBrowser(headless=True, user_agent="MyScraper") as context:
            # Use the context instance here
            ...
    """

    def __init__(
        self, headless: bool = True, proxy: Proxy | None = None, **context_kwargs
    ):
        """Initializes the PlaywrightBrowser context manager.

        Args:
            headless: Whether to run the browser in headless mode.
            proxy: The proxy settings to use.
            **context_kwargs: Additional keyword arguments to pass to `browser.new_context()`.
        """
        self.headless = headless
        self.proxy = proxy.get_playwright_proxy() if proxy else None
        self._playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.context_kwargs = context_kwargs

    def __enter__(self) -> BrowserContext:
        """Starts Playwright, launches a browser, and creates a context."""
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(
            headless=self.headless, proxy=self.proxy
        )
        self.context = self.browser.new_context(**self.context_kwargs)
        return self.context

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Closes the context, browser, and stops Playwright."""
        # The context must be closed before the browser.
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self._playwright:
            self._playwright.stop()


class DownloadProcess:
    """
    A process to perform various download actions on a URL in a single navigation.

    This class can download the HTML, capture API responses, and download files
    triggered by navigation, all with a single `page.goto()` call.

    Attributes:
        config (Config): The application configuration object.
    """

    def __init__(self, config: Config):
        """Initializes the DownloadProcess.

        Args:
            config: The application configuration object.
        """
        self.config = config

    def download(
        self,
        context: BrowserContext,
        tasks: Union[List[DownloadTask], DownloadTask],
    ) -> None:
        """
        Executes one or more download tasks. A single page is created and reused
        for all tasks in the list.

        Args:
            context: The Playwright BrowserContext instance to use.
            tasks: A single DownloadTask or a list of them.
        """
        if not isinstance(tasks, list):
            tasks = [tasks]

        with context.new_page() as page:
            for task in tasks:
                self._do_download(page, task)

    def _do_download(self, page: Page, task: DownloadTask) -> None:
        """Performs the actual download logic for a single task."""
        api_response_handler = None
        if task.capture_api_urls:
            # Assign to a local variable to help mypy with type narrowing inside the closure.
            urls_to_capture = task.capture_api_urls
            counter = incremental_counter()

            def on_response(response: Response) -> None:
                """Callback to process and save responses."""
                # The check `if task.capture_api_urls:` above ensures this list is not None.
                if not any(u in response.url for u in urls_to_capture):
                    return

                parsed_url = urlparse(response.url)
                filename_base = os.path.basename(parsed_url.path) or "api_response"
                ext = ".json" if task.capture_api_response_fn == "json" else ".txt"
                unique_id = next(counter)
                filename = f"{filename_base}_{unique_id}{ext}"

                content: str | dict = (
                    response.json()
                    if task.capture_api_response_fn == "json"
                    else response.text()
                )

                self.config.logger.info(f"Captured API response from {response.url}")
                file_to_save = cast(
                    File,
                    task.capture_api_file_type(
                        config=self.config,
                        content=content,
                        path_or_name=filename,
                        subdir=task.capture_api_subdir,
                    ),
                )
                file_to_save.save(clear_content=True)

            api_response_handler = on_response
            page.on("response", api_response_handler)

        try:
            # Handle file download and navigation together
            if task.download_file:
                with page.expect_download() as download_info:
                    try:
                        self.config.logger.info(
                            f"Navigating to {task.url} to download file..."
                        )
                        page.goto(task.url)  # wait_until="load" might fail here
                    except Error as playwright_error:
                        if 'waiting until "load"' in str(playwright_error):
                            self.config.logger.debug(
                                "Page load interrupted by file download, as expected."
                            )
                        else:
                            raise playwright_error

                download: Download = download_info.value
                self.config.logger.info(
                    f"Saving downloaded file to {task.download_file.path}"
                )
                with open(download.path(), "rb") as f:
                    task.download_file.save(f.read())
            else:
                # Just navigate if no file download is expected
                page.goto(task.url, wait_until="load")

            # Process HTML after navigation
            if task.html_file:
                initial_html = page.content()
                initial_soup = BeautifulSoup(initial_html, "html.parser")
                task.html_file.content = str(initial_soup)
                self.config.logger.info(
                    f"Saving HTML from {task.url} to {task.html_file.path}"
                )
                task.html_file.save()

        finally:
            # Cleanup API listener
            if api_response_handler:
                page.remove_listener("response", api_response_handler)
