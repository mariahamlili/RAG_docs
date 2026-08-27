from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from scraper.config import AppConfig
from scraper.extract import extract_document


class Crawl4AIBackendError(RuntimeError):
    pass


@dataclass
class Crawl4AIDocument:
    title: str
    text: str
    cleaned_html: str
    raw_html: str
    via: str
    status_code: int | None


def _markdown_to_text(markdown_payload: Any) -> str:
    if markdown_payload is None:
        return ""
    fit_markdown = getattr(markdown_payload, "fit_markdown", None)
    if isinstance(fit_markdown, str) and fit_markdown.strip():
        return fit_markdown.strip()
    raw_markdown = getattr(markdown_payload, "raw_markdown", None)
    if isinstance(raw_markdown, str) and raw_markdown.strip():
        return raw_markdown.strip()
    if isinstance(markdown_payload, str):
        return markdown_payload.strip()
    return ""


async def _crawl_page(url: str, config: AppConfig) -> Crawl4AIDocument:
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
    except ImportError as exc:
        raise Crawl4AIBackendError(
            "crawl4ai is not installed. Install requirements and run crawl4ai-setup."
        ) from exc

    browser_config = BrowserConfig(headless=config.headless_browser, verbose=False)
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config, magic=config.crawl4ai_magic)

    raw_html = getattr(result, "cleaned_html", None) or getattr(result, "html", None) or ""
    if not isinstance(raw_html, str) or not raw_html.strip():
        raise Crawl4AIBackendError(f"crawl4ai returned no HTML for {url}")

    extracted = extract_document(raw_html, url)
    markdown_text = _markdown_to_text(getattr(result, "markdown", None))
    status_code = getattr(result, "status_code", None)

    return Crawl4AIDocument(
        title=extracted.title,
        text=markdown_text or extracted.text,
        cleaned_html=extracted.cleaned_html,
        raw_html=raw_html,
        via="crawl4ai",
        status_code=status_code if isinstance(status_code, int) else None,
    )


def crawl_page(url: str, config: AppConfig) -> Crawl4AIDocument:
    try:
        return asyncio.run(_crawl_page(url, config))
    except Crawl4AIBackendError:
        raise
    except Exception as exc:
        raise Crawl4AIBackendError(f"crawl4ai failed for {url}: {exc}") from exc