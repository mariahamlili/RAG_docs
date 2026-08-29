from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from scraper.config import AppConfig


class FetchError(RuntimeError):
    pass


@dataclass
class FetchedResponse:
    url: str
    status_code: int
    content_type: str
    content: bytes
    text: str | None
    headers: dict[str, str]
    via: str


class Fetcher:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=config.request_timeout,
            verify=config.verify_ssl,
            headers={"User-Agent": config.user_agent},
        )
        self._last_request_time = 0.0
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._context: Any | None = None
        self._page: Any | None = None

    def close(self) -> None:
        self.client.close()
        if self._page is not None:
            self._page.close()
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _respect_delay(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        remaining = self.config.request_delay_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _mark_request(self) -> None:
        self._last_request_time = time.monotonic()

    @staticmethod
    def _looks_like_bot_challenge(status_code: int, headers: dict[str, str], text: str) -> bool:
        lowered_text = text.lower()
        lowered_headers = {key.lower(): value.lower() for key, value in headers.items()}
        if status_code in {403, 429, 503}:
            return True
        if lowered_headers.get("cf-mitigated") == "challenge":
            return True
        return "cloudflare" in lowered_text and "just a moment" in lowered_text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((httpx.HTTPError, FetchError)),
        reraise=True,
    )
    def fetch(self, url: str, *, binary: bool = False) -> FetchedResponse:
        self._respect_delay()
        response = self.client.get(url)
        self._mark_request()

        content_type = response.headers.get("content-type", "")
        text = None if binary else response.text
        headers = dict(response.headers)

        if not binary and self.config.use_browser_fallback and self._looks_like_bot_challenge(
            response.status_code, headers, text or ""
        ):
            browser_response = self._fetch_with_browser(url)
            if browser_response is not None:
                return browser_response

        content = response.content
        if response.status_code >= 400:
            raise FetchError(f"HTTP {response.status_code} for {url}")

        return FetchedResponse(
            url=str(response.url),
            status_code=response.status_code,
            content_type=content_type,
            content=content,
            text=text,
            headers=headers,
            via="httpx",
        )

    def _ensure_browser(self) -> None:
        if self._page is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise FetchError("Playwright is not installed") from exc

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.config.headless_browser
        )
        self._context = self._browser.new_context(user_agent=self.config.user_agent)
        self._page = self._context.new_page()

    def _fetch_with_browser(self, url: str) -> FetchedResponse | None:
        try:
            self._ensure_browser()
            response = self._page.goto(
                url,
                wait_until="networkidle",
                timeout=self.config.request_timeout * 1000,
            )
            html = self._page.content()
            body_text = self._page.locator("body").inner_text()
            headers = dict(response.headers) if response else {}
            content_type = headers.get("content-type", "text/html")
            status_code = response.status if response else 200
            content = body_text.encode("utf-8") if "xml" in content_type else html.encode("utf-8")
            text = body_text if "xml" in content_type else html
            if status_code >= 400:
                raise FetchError(f"Browser fetch failed with HTTP {status_code} for {url}")
            return FetchedResponse(
                url=url,
                status_code=status_code,
                content_type=content_type,
                content=content,
                text=text,
                headers=headers,
                via="playwright",
            )
        except Exception as exc:
            raise FetchError(f"Browser fallback failed for {url}: {exc}") from exc
