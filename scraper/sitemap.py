from __future__ import annotations

import gzip
import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import urljoin

from scraper.fetch import FetchError, Fetcher


@dataclass
class SitemapParseResult:
    kind: str
    locations: list[str]


def parse_robots_for_sitemaps(robots_text: str, root_url: str) -> list[str]:
    sitemap_urls: list[str] = []
    for raw_line in robots_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("sitemap:"):
            location = line.split(":", 1)[1].strip()
            sitemap_urls.append(urljoin(root_url, location))
    return sitemap_urls


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _decode_payload(content: bytes, url: str, content_type: str) -> str:
    if url.endswith(".gz") or "gzip" in content_type.lower():
        with gzip.GzipFile(fileobj=io.BytesIO(content)) as handle:
            return handle.read().decode("utf-8")
    return content.decode("utf-8", errors="replace")


def parse_sitemap_xml(xml_text: str) -> SitemapParseResult:
    root = ET.fromstring(xml_text)
    root_name = _local_name(root.tag)

    if root_name == "sitemapindex":
        locations = [
            element.text.strip()
            for element in root.findall("{*}sitemap/{*}loc")
            if element.text and element.text.strip()
        ]
        return SitemapParseResult(kind="sitemapindex", locations=locations)

    if root_name == "urlset":
        locations = [
            element.text.strip()
            for element in root.findall("{*}url/{*}loc")
            if element.text and element.text.strip()
        ]
        return SitemapParseResult(kind="urlset", locations=locations)

    raise ValueError(f"Unsupported sitemap root tag: {root_name}")


def discover_sitemap_entrypoints(root_url: str, fetcher: Fetcher, candidates: list[str]) -> list[str]:
    discovered: list[str] = []

    try:
        robots_response = fetcher.fetch(urljoin(root_url, "/robots.txt"))
        discovered.extend(parse_robots_for_sitemaps(robots_response.text or "", root_url))
    except (FetchError, ValueError):
        pass

    for candidate in candidates:
        candidate_url = urljoin(root_url, candidate)
        if candidate_url in discovered:
            continue
        try:
            response = fetcher.fetch(candidate_url)
            xml_text = _decode_payload(response.content, response.url, response.content_type)
            parse_sitemap_xml(xml_text)
            discovered.append(candidate_url)
        except (FetchError, ET.ParseError, ValueError, OSError):
            continue

    return sorted(set(discovered))


def expand_sitemaps(
    entrypoints: list[str], fetcher: Fetcher
) -> tuple[list[dict], list[dict]]:
    queue = list(entrypoints)
    seen = set()
    sitemap_records: list[dict] = []
    url_records: list[dict] = []

    while queue:
        sitemap_url = queue.pop(0)
        if sitemap_url in seen:
            continue
        seen.add(sitemap_url)

        response = fetcher.fetch(sitemap_url)
        xml_text = _decode_payload(response.content, response.url, response.content_type)
        parsed = parse_sitemap_xml(xml_text)

        sitemap_records.append(
            {
                "sitemap_url": sitemap_url,
                "kind": parsed.kind,
                "child_count": len(parsed.locations),
                "fetched_via": response.via,
            }
        )

        if parsed.kind == "sitemapindex":
            queue.extend(parsed.locations)
            continue

        for page_url in parsed.locations:
            url_records.append(
                {
                    "url": page_url,
                    "sitemap_origin": sitemap_url,
                }
            )

    return sitemap_records, url_records
