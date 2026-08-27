from __future__ import annotations

from collections import deque
from pathlib import Path
from shutil import copyfile
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from scraper.classify import classify_url, is_pdf_asset
from scraper.config import AppConfig
from scraper.crawl4ai_backend import crawl_page
from scraper.extract import extract_document
from scraper.fetch import Fetcher
from scraper.manifest import (
    DocumentManifestRecord,
    SitemapInventoryRecord,
    utc_now_iso,
    write_json_manifest,
    write_jsonl_manifest,
)
from scraper.render_pdf import render_html_to_pdf
from scraper.sitemap import discover_sitemap_entrypoints, expand_sitemaps
from scraper.utils import (
    append_jsonl,
    extension_from_url,
    extract_internal_links,
    is_same_scope,
    normalize_url,
    path_from_url,
    sha256_bytes,
    slug_from_url,
)

app = typer.Typer(help="Sitemap-first site ingestion for RAG document preparation.")
console = Console()


def load_config(config_path: Optional[Path]) -> AppConfig:
    return AppConfig.load(config_path)


def _inventory_path(config: AppConfig) -> Path:
    return config.output_dir / "manifests" / "url_inventory.jsonl"


def _sitemap_manifest_path(config: AppConfig) -> Path:
    return config.output_dir / "manifests" / "sitemaps.json"


def _document_manifest_path(config: AppConfig) -> Path:
    return config.output_dir / "manifests" / "documents.jsonl"


def _crawl_inventory_path(config: AppConfig) -> Path:
    return config.output_dir / "manifests" / "crawl_inventory.jsonl"


@app.command()
def discover(
    root_url: str = typer.Option(..., help="Root domain used for robots.txt and sitemap probing."),
    config: Optional[Path] = typer.Option(None, help="Path to config YAML."),
) -> None:
    app_config = load_config(config)
    app_config.ensure_directories()

    with Fetcher(app_config) as fetcher:
        sitemap_urls = discover_sitemap_entrypoints(
            root_url, fetcher, app_config.sitemap_candidates
        )

    manifest = {
        "root_url": root_url,
        "discovered_at": utc_now_iso(),
        "sitemaps": sitemap_urls,
        "config": app_config.dump(),
    }
    write_json_manifest(_sitemap_manifest_path(app_config), manifest)

    table = Table(title="Discovered Sitemaps")
    table.add_column("URL")
    for sitemap_url in sitemap_urls:
        table.add_row(sitemap_url)
    console.print(table)


@app.command()
def inventory(
    root_url: str = typer.Option(..., help="Root domain used for sitemap expansion."),
    config: Optional[Path] = typer.Option(None, help="Path to config YAML."),
) -> None:
    app_config = load_config(config)
    app_config.ensure_directories()

    with Fetcher(app_config) as fetcher:
        sitemap_urls = discover_sitemap_entrypoints(
            root_url, fetcher, app_config.sitemap_candidates
        )
        sitemap_records, discovered_urls = expand_sitemaps(sitemap_urls, fetcher)

    records: list[SitemapInventoryRecord] = []
    seen = set()
    for item in discovered_urls:
        normalized = normalize_url(item["url"], app_config.ignored_query_prefixes)
        if normalized in seen:
            continue
        if not is_same_scope(root_url, normalized, app_config.follow_subdomains):
            continue
        seen.add(normalized)
        records.append(
            SitemapInventoryRecord(
                url=item["url"],
                normalized_url=normalized,
                source_type=classify_url(normalized),
                sitemap_origin=item["sitemap_origin"],
            )
        )

    write_json_manifest(
        _sitemap_manifest_path(app_config),
        {
            "root_url": root_url,
            "discovered_at": utc_now_iso(),
            "sitemaps": sitemap_urls,
            "expanded_sitemaps": sitemap_records,
            "url_count": len(records),
            "config": app_config.dump(),
        },
    )
    write_jsonl_manifest(_inventory_path(app_config), records)

    table = Table(title="Inventory Summary")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Sitemaps", str(len(sitemap_records)))
    table.add_row("Unique URLs", str(len(records)))
    console.print(table)


@app.command("crawl-links")
def crawl_links(
    root_url: str = typer.Option(..., help="Root domain used to filter internal links."),
    config: Optional[Path] = typer.Option(None, help="Path to config YAML."),
    start_url: Optional[str] = typer.Option(None, help="Optional start page. Defaults to root URL."),
    max_pages: int = typer.Option(25, help="Maximum number of HTML pages to fetch during discovery."),
    max_depth: int = typer.Option(2, help="Maximum link depth from the start URL."),
    inventory_path: Optional[Path] = typer.Option(None, help="Optional output path for the discovered inventory."),
) -> None:
    app_config = load_config(config)
    app_config.ensure_directories()

    start = normalize_url(start_url or root_url, app_config.ignored_query_prefixes)
    queue = deque([(start, 0, None)])
    queued = {start}
    visited = set()
    inventory: dict[str, dict] = {}

    def ensure_record(url: str, depth: int, discovered_from: str | None) -> dict:
        record = inventory.get(url)
        if record is None:
            record = {
                "url": url,
                "normalized_url": url,
                "source_type": classify_url(url),
                "sitemap_origin": f"crawl:{start}",
                "discovered_from": discovered_from,
                "depth": depth,
                "fetched": False,
                "outlink_count": 0,
            }
            inventory[url] = record
            return record

        if discovered_from is not None and record.get("discovered_from") is None:
            record["discovered_from"] = discovered_from
        if depth < int(record.get("depth", depth)):
            record["depth"] = depth
        return record

    with Fetcher(app_config) as fetcher:
        while queue and len(visited) < max_pages:
            current_url, depth, discovered_from = queue.popleft()
            if current_url in visited:
                continue
            visited.add(current_url)

            current_record = ensure_record(current_url, depth, discovered_from)
            if current_record["source_type"] != "html":
                continue

            try:
                if app_config.html_backend == "crawl4ai":
                    crawled = crawl_page(current_url, app_config)
                    html = crawled.raw_html
                else:
                    response = fetcher.fetch(current_url)
                    html = response.text or response.content.decode("utf-8", errors="replace")
            except Exception as exc:
                current_record["error"] = str(exc)
                continue

            current_record["fetched"] = True
            discovered_links = extract_internal_links(
                html,
                page_url=current_url,
                root_url=root_url,
                ignored_prefixes=app_config.ignored_query_prefixes,
                follow_subdomains=app_config.follow_subdomains,
            )
            current_record["outlink_count"] = len(discovered_links)

            if depth >= max_depth:
                continue

            for link in discovered_links:
                link_depth = depth + 1
                record = ensure_record(link, link_depth, current_url)
                if record["source_type"] != "html":
                    continue
                if link in visited or link in queued:
                    continue
                queued.add(link)
                queue.append((link, link_depth, current_url))

    output_path = inventory_path or _crawl_inventory_path(app_config)
    records = sorted(inventory.values(), key=lambda item: (item["depth"], item["normalized_url"]))
    append_jsonl(output_path, records)

    fetched_count = sum(1 for item in records if item.get("fetched"))
    error_count = sum(1 for item in records if item.get("error"))
    table = Table(title="Crawl Link Inventory")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Discovered URLs", str(len(records)))
    table.add_row("Fetched HTML pages", str(fetched_count))
    table.add_row("Errors", str(error_count))
    table.add_row("Output", str(output_path))
    console.print(table)


def _save_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@app.command()
def ingest(
    root_url: str = typer.Option(..., help="Root domain used to filter URLs."),
    config: Optional[Path] = typer.Option(None, help="Path to config YAML."),
    limit: Optional[int] = typer.Option(None, help="Only ingest the first N records for sampling."),
    inventory_path: Optional[Path] = typer.Option(None, help="Optional explicit inventory path."),
) -> None:
    app_config = load_config(config)
    directories = app_config.ensure_directories()
    inventory_file = inventory_path or _inventory_path(app_config)
    if not inventory_file.exists():
        raise typer.BadParameter(
            f"Inventory file not found: {inventory_file}. Run the inventory command first."
        )

    lines = inventory_file.read_text(encoding="utf-8").splitlines()
    selected_lines = lines[:limit] if limit else lines
    records = [SitemapInventoryRecord.model_validate_json(line) for line in selected_lines]

    manifest_records: list[DocumentManifestRecord] = []

    with Fetcher(app_config) as fetcher:
        for record in records:
            if not is_same_scope(root_url, record.normalized_url, app_config.follow_subdomains):
                continue

            source_extension = extension_from_url(record.normalized_url)
            raw_path = path_from_url(record.normalized_url, directories["raw"], source_extension)
            text_path = path_from_url(record.normalized_url, directories["text"], ".txt")
            pdf_path = path_from_url(record.normalized_url, directories["pdf"], ".pdf")

            try:
                if record.source_type == "html" and app_config.html_backend == "crawl4ai":
                    crawled = crawl_page(record.normalized_url, app_config)
                    raw_payload = crawled.raw_html.encode("utf-8")
                    _save_bytes(raw_path, raw_payload)
                    _save_text(text_path, crawled.text)
                    render_html_to_pdf(crawled.cleaned_html, pdf_path, base_url=record.normalized_url)
                    manifest_records.append(
                        DocumentManifestRecord(
                            source_url=record.normalized_url,
                            source_type=record.source_type,
                            title=crawled.title,
                            local_raw_path=str(raw_path),
                            local_text_path=str(text_path),
                            local_pdf_path=str(pdf_path),
                            fetch_via=crawled.via,
                            http_status=crawled.status_code,
                            content_hash=sha256_bytes(raw_payload),
                            sitemap_origin=record.sitemap_origin,
                            fetched_at=utc_now_iso(),
                        )
                    )
                    continue

                response = fetcher.fetch(
                    record.normalized_url, binary=record.source_type.startswith("asset:")
                )
                _save_bytes(raw_path, response.content)
                payload_hash = sha256_bytes(response.content)

                if record.source_type == "html":
                    html_text = response.text or response.content.decode("utf-8", errors="replace")
                    extracted = extract_document(html_text, record.normalized_url)
                    _save_text(text_path, extracted.text)
                    render_html_to_pdf(extracted.cleaned_html, pdf_path, base_url=record.normalized_url)
                    manifest_records.append(
                        DocumentManifestRecord(
                            source_url=record.normalized_url,
                            source_type=record.source_type,
                            title=extracted.title,
                            local_raw_path=str(raw_path),
                            local_text_path=str(text_path),
                            local_pdf_path=str(pdf_path),
                            fetch_via=response.via,
                            http_status=response.status_code,
                            content_hash=payload_hash,
                            sitemap_origin=record.sitemap_origin,
                            fetched_at=utc_now_iso(),
                        )
                    )
                    continue

                if is_pdf_asset(record.normalized_url):
                    copyfile(raw_path, pdf_path)
                    manifest_records.append(
                        DocumentManifestRecord(
                            source_url=record.normalized_url,
                            source_type=record.source_type,
                            title=Path(record.normalized_url).name,
                            local_raw_path=str(raw_path),
                            local_pdf_path=str(pdf_path),
                            fetch_via=response.via,
                            http_status=response.status_code,
                            content_hash=payload_hash,
                            sitemap_origin=record.sitemap_origin,
                            fetched_at=utc_now_iso(),
                        )
                    )
                    continue

                manifest_records.append(
                    DocumentManifestRecord(
                        source_url=record.normalized_url,
                        source_type=record.source_type,
                        title=Path(record.normalized_url).name,
                        local_raw_path=str(raw_path),
                        fetch_via=response.via,
                        http_status=response.status_code,
                        content_hash=payload_hash,
                        sitemap_origin=record.sitemap_origin,
                        fetched_at=utc_now_iso(),
                    )
                )
            except Exception as exc:
                manifest_records.append(
                    DocumentManifestRecord(
                        source_url=record.normalized_url,
                        source_type=record.source_type,
                        sitemap_origin=record.sitemap_origin,
                        fetched_at=utc_now_iso(),
                        error=str(exc),
                    )
                )

    write_jsonl_manifest(_document_manifest_path(app_config), manifest_records)

    success_count = sum(1 for item in manifest_records if item.error is None)
    failure_count = len(manifest_records) - success_count
    table = Table(title="Ingest Summary")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Processed", str(len(manifest_records)))
    table.add_row("Succeeded", str(success_count))
    table.add_row("Failed", str(failure_count))
    console.print(table)


if __name__ == "__main__":
    app()
