from __future__ import annotations

from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from shutil import copyfile
from threading import Lock, local
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from scraper.classify import classify_url, is_pdf_asset
from scraper.config import AppConfig
from scraper.corpus_filter import run_corpus_filter
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
from scraper.organize import (
    breadcrumb_for,
    build_destination,
    collapse_small_folders,
    destination_root,
    library_kind_for,
    topic_path_for,
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


def _library_plan_path(config: AppConfig) -> Path:
    return config.output_dir / "manifests" / "library_plan.jsonl"


def _pdf_library_path(config: AppConfig) -> Path:
    return config.output_dir / "manifests" / "pdf_library.jsonl"


def _document_manifest_path(config: AppConfig) -> Path:
    return config.output_dir / "manifests" / "documents.jsonl"


def _crawl_inventory_path(config: AppConfig) -> Path:
    return config.output_dir / "manifests" / "crawl_inventory.jsonl"


def _parse_library_types(types: str) -> set[str]:
    requested = {part.strip().lower() for part in types.split(",") if part.strip()}
    allowed = {"pdf", "office", "html"}
    unknown = requested - allowed
    if unknown:
        raise typer.BadParameter(f"Unknown types {sorted(unknown)}; allowed: pdf,office,html")
    return requested or allowed


def _inventory_matches_types(source_type: str, types: set[str]) -> bool:
    if source_type == "html":
        return "html" in types
    if source_type == "asset:pdf":
        return "pdf" in types
    if source_type.startswith("asset:"):
        return "office" in types
    return False


def _load_inventory_records(inventory_file: Path) -> list[dict]:
    records: list[dict] = []
    for line in inventory_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(SitemapInventoryRecord.model_validate_json(line).model_dump())
    return records


def _build_library_plan(records: list[dict], types: set[str]) -> list[dict]:
    selected = [row for row in records if _inventory_matches_types(row["source_type"], types)]
    draft_assignments: list[tuple[tuple[str, ...], str]] = []
    for row in selected:
        topic = topic_path_for(
            row["normalized_url"],
            source_type=row["source_type"],
            discovered_from=row.get("discovered_from"),
        )
        draft_assignments.append((topic, row["normalized_url"]))

    collapsed = collapse_small_folders(draft_assignments)
    taken_by_folder: dict[tuple[str, ...], set[str]] = {}
    plan_rows: list[dict] = []

    for row in selected:
        topic_parts = collapsed[row["normalized_url"]]
        folder_key = (library_kind_for(row["source_type"]),) + topic_parts
        taken = taken_by_folder.setdefault(folder_key, set())
        destination = build_destination(
            source_url=row["normalized_url"],
            source_type=row["source_type"],
            discovered_from=row.get("discovered_from"),
            topic_parts=topic_parts,
            taken_in_folder=taken,
        )
        plan_rows.append(
            {
                "source_url": row["normalized_url"],
                "source_type": row["source_type"],
                "discovered_from": row.get("discovered_from"),
                "sitemap_origin": row.get("sitemap_origin"),
                "library_kind": destination.library_kind,
                "topic_path": destination.topic_path,
                "topic_breadcrumb": breadcrumb_for(destination.topic_parts),
                "domain": destination.domain,
                "relative_path": destination.relative_path,
                "filename": destination.filename,
            }
        )

    kind_order = {"source_pdf": 0, "office": 1, "rendered_pdf": 2}
    plan_rows.sort(key=lambda row: (kind_order.get(row["library_kind"], 9), row["topic_path"], row["source_url"]))
    return plan_rows


def _is_valid_pdf_bytes(payload: bytes, content_type: str) -> bool:
    if not payload.startswith(b"%PDF"):
        return False
    lowered = (content_type or "").lower()
    if "html" in lowered or lowered.startswith("text/"):
        return False
    return True


def _file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return sha256_bytes(path.read_bytes())


_render_lock = Lock()
_worker_state = local()


def _process_library_item(
    *,
    index: int,
    total: int,
    plan: dict,
    app_config: AppConfig,
    directories: dict[str, Path],
    rejected_dir: Path,
    resume: bool,
    fetcher: Fetcher,
) -> tuple[dict, DocumentManifestRecord, str]:
    source_url = plan["source_url"]
    source_type = plan["source_type"]
    kind = plan["library_kind"]
    root = destination_root(kind, app_config.output_dir)
    dest_path = root / plan["relative_path"]
    topic_path = plan["topic_path"]

    console.print(f"[{index}/{total}] {kind} {source_url}")

    if resume and dest_path.exists() and dest_path.stat().st_size > 0:
        content_hash = _file_sha256(dest_path) or ""
        library_record = {
            **plan,
            "local_path": str(dest_path),
            "content_hash": content_hash,
            "bytes": dest_path.stat().st_size,
            "http_status": None,
            "fetch_via": "resume",
            "fetched_at": utc_now_iso(),
            "status": "skipped",
        }
        document_record = DocumentManifestRecord(
            source_url=source_url,
            source_type=source_type,
            title=plan["filename"],
            local_pdf_path=str(dest_path) if kind.endswith("pdf") else None,
            local_raw_path=str(dest_path) if kind == "office" else None,
            content_hash=content_hash,
            discovered_from=plan.get("discovered_from"),
            topic_path=topic_path,
            library_kind=kind,
            sitemap_origin=plan.get("sitemap_origin"),
            fetched_at=utc_now_iso(),
        )
        return library_record, document_record, "skipped"

    if source_type == "html":
        if app_config.html_backend == "crawl4ai":
            crawled = crawl_page(source_url, app_config)
            raw_payload = crawled.raw_html.encode("utf-8")
            raw_path = path_from_url(source_url, directories["raw"], ".html")
            text_path = path_from_url(source_url, directories["text"], ".txt")
            _save_bytes(raw_path, raw_payload)
            _save_text(text_path, crawled.text)
            with _render_lock:
                render_html_to_pdf(crawled.cleaned_html, dest_path, base_url=source_url)
            content_hash = sha256_bytes(raw_payload)
            fetch_via = crawled.via
            http_status = crawled.status_code
            title = crawled.title
        else:
            response = fetcher.fetch(source_url, binary=False)
            raw_path = path_from_url(source_url, directories["raw"], ".html")
            text_path = path_from_url(source_url, directories["text"], ".txt")
            _save_bytes(raw_path, response.content)
            html_text = response.text or response.content.decode("utf-8", errors="replace")
            extracted = extract_document(html_text, source_url)
            _save_text(text_path, extracted.text)
            with _render_lock:
                render_html_to_pdf(extracted.cleaned_html, dest_path, base_url=source_url)
            content_hash = sha256_bytes(response.content)
            fetch_via = response.via
            http_status = response.status_code
            title = extracted.title

        library_record = {
            **plan,
            "local_path": str(dest_path),
            "local_raw_path": str(raw_path),
            "local_text_path": str(text_path),
            "content_hash": content_hash,
            "bytes": dest_path.stat().st_size if dest_path.exists() else 0,
            "http_status": http_status,
            "fetch_via": fetch_via,
            "fetched_at": utc_now_iso(),
            "status": "fetched",
            "title": title,
        }
        document_record = DocumentManifestRecord(
            source_url=source_url,
            source_type=source_type,
            title=title,
            local_raw_path=str(raw_path),
            local_text_path=str(text_path),
            local_pdf_path=str(dest_path),
            fetch_via=fetch_via,
            http_status=http_status,
            content_hash=content_hash,
            discovered_from=plan.get("discovered_from"),
            topic_path=topic_path,
            library_kind=kind,
            sitemap_origin=plan.get("sitemap_origin"),
            fetched_at=utc_now_iso(),
        )
        return library_record, document_record, "fetched"

    response = fetcher.fetch(source_url, binary=True)
    payload = response.content
    content_hash = sha256_bytes(payload)

    if source_type == "asset:pdf" and not _is_valid_pdf_bytes(payload, response.content_type):
        reject_path = rejected_dir / f"{slug_from_url(source_url)}.bin"
        _save_bytes(reject_path, payload)
        library_record = {
            **plan,
            "local_path": str(reject_path),
            "content_hash": content_hash,
            "bytes": len(payload),
            "http_status": response.status_code,
            "fetch_via": response.via,
            "fetched_at": utc_now_iso(),
            "status": "rejected",
            "error": f"Invalid PDF content-type={response.content_type}",
        }
        document_record = DocumentManifestRecord(
            source_url=source_url,
            source_type=source_type,
            discovered_from=plan.get("discovered_from"),
            topic_path=topic_path,
            library_kind=kind,
            sitemap_origin=plan.get("sitemap_origin"),
            fetched_at=utc_now_iso(),
            error=f"Invalid PDF content-type={response.content_type}",
        )
        return library_record, document_record, "rejected"

    _save_bytes(dest_path, payload)
    library_record = {
        **plan,
        "local_path": str(dest_path),
        "content_hash": content_hash,
        "bytes": len(payload),
        "http_status": response.status_code,
        "fetch_via": response.via,
        "fetched_at": utc_now_iso(),
        "status": "fetched",
        "title": plan["filename"],
    }
    document_record = DocumentManifestRecord(
        source_url=source_url,
        source_type=source_type,
        title=plan["filename"],
        local_raw_path=str(dest_path) if kind == "office" else None,
        local_pdf_path=str(dest_path) if kind == "source_pdf" else None,
        fetch_via=response.via,
        http_status=response.status_code,
        content_hash=content_hash,
        discovered_from=plan.get("discovered_from"),
        topic_path=topic_path,
        library_kind=kind,
        sitemap_origin=plan.get("sitemap_origin"),
        fetched_at=utc_now_iso(),
    )
    return library_record, document_record, "fetched"


def _run_library_item(
    *,
    index: int,
    total: int,
    plan: dict,
    app_config: AppConfig,
    directories: dict[str, Path],
    rejected_dir: Path,
    resume: bool,
) -> tuple[dict, DocumentManifestRecord, str]:
    fetcher = getattr(_worker_state, "fetcher", None)
    if fetcher is None:
        fetcher = Fetcher(app_config)
        _worker_state.fetcher = fetcher
    try:
        return _process_library_item(
            index=index,
            total=total,
            plan=plan,
            app_config=app_config,
            directories=directories,
            rejected_dir=rejected_dir,
            resume=resume,
            fetcher=fetcher,
        )
    except Exception as exc:
        library_record = {
            **plan,
            "fetched_at": utc_now_iso(),
            "status": "failed",
            "error": str(exc),
        }
        document_record = DocumentManifestRecord(
            source_url=plan["source_url"],
            source_type=plan["source_type"],
            discovered_from=plan.get("discovered_from"),
            topic_path=plan.get("topic_path"),
            library_kind=plan.get("library_kind"),
            sitemap_origin=plan.get("sitemap_origin"),
            fetched_at=utc_now_iso(),
            error=str(exc),
        )
        return library_record, document_record, "failed"


@app.command("fetch-library")
def fetch_library(
    inventory_path: Path = typer.Option(
        Path("data/manifests/agriculture_full_inventory.jsonl"),
        help="Inventory JSONL to fetch from.",
    ),
    config: Optional[Path] = typer.Option(
        Path("config.agriculture.yaml"),
        help="Path to config YAML.",
    ),
    types: str = typer.Option("pdf,office,html", help="Comma-separated: pdf,office,html"),
    limit: Optional[int] = typer.Option(None, help="Only process the first N planned records."),
    resume: bool = typer.Option(True, help="Skip files that already exist on disk."),
    plan_path: Optional[Path] = typer.Option(None, help="Optional existing plan JSONL."),
    workers: int = typer.Option(8, min=1, max=32, help="Parallel worker threads."),
) -> None:
    app_config = load_config(config)
    directories = app_config.ensure_directories()
    (app_config.output_dir / "pdf" / "source").mkdir(parents=True, exist_ok=True)
    (app_config.output_dir / "pdf" / "rendered").mkdir(parents=True, exist_ok=True)
    rejected_dir = app_config.output_dir / "pdf" / "_rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    (app_config.output_dir / "office").mkdir(parents=True, exist_ok=True)

    if not inventory_path.exists():
        raise typer.BadParameter(f"Inventory file not found: {inventory_path}")

    selected_types = _parse_library_types(types)
    records = _load_inventory_records(inventory_path)
    if plan_path and plan_path.exists():
        plan_rows = [
            __import__("json").loads(line)
            for line in plan_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        plan_rows = [row for row in plan_rows if _inventory_matches_types(row["source_type"], selected_types)]
    else:
        plan_rows = _build_library_plan(records, selected_types)
        append_jsonl(_library_plan_path(app_config), plan_rows)

    if limit is not None:
        plan_rows = plan_rows[:limit]

    document_records: list[DocumentManifestRecord] = []
    library_records: list[dict] = []
    stats = {"fetched": 0, "skipped": 0, "rejected": 0, "failed": 0}
    total = len(plan_rows)
    console.print(f"Fetching {total} records with {workers} workers")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _run_library_item,
                index=index,
                total=total,
                plan=plan,
                app_config=app_config,
                directories=directories,
                rejected_dir=rejected_dir,
                resume=resume,
            )
            for index, plan in enumerate(plan_rows, start=1)
        ]
        for future in as_completed(futures):
            library_record, document_record, status = future.result()
            library_records.append(library_record)
            document_records.append(document_record)
            stats[status] = stats.get(status, 0) + 1

    # Close thread-local fetchers created during the run.
    # ThreadPoolExecutor workers are gone; open clients are finalized with process GC.

    append_jsonl(_pdf_library_path(app_config), library_records)
    write_jsonl_manifest(_document_manifest_path(app_config), document_records)

    hashes: dict[str, list[str]] = {}
    for row in library_records:
        digest = row.get("content_hash")
        if digest and row.get("status") in {"fetched", "skipped"}:
            hashes.setdefault(digest, []).append(row["source_url"])
    duplicates = sum(1 for urls in hashes.values() if len(urls) > 1)

    table = Table(title="Fetch Library Summary")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Planned", str(len(plan_rows)))
    table.add_row("Workers", str(workers))
    table.add_row("Fetched", str(stats["fetched"]))
    table.add_row("Skipped", str(stats["skipped"]))
    table.add_row("Rejected", str(stats["rejected"]))
    table.add_row("Failed", str(stats["failed"]))
    table.add_row("Duplicate hashes", str(duplicates))
    table.add_row("pdf_library", str(_pdf_library_path(app_config)))
    table.add_row("documents", str(_document_manifest_path(app_config)))
    console.print(table)


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


@app.command("plan-library")
def plan_library(
    inventory_path: Path = typer.Option(
        Path("data/manifests/agriculture_full_inventory.jsonl"),
        help="Inventory JSONL used to plan destinations.",
    ),
    config: Optional[Path] = typer.Option(None, help="Path to config YAML."),
    types: str = typer.Option("pdf,office,html", help="Comma-separated: pdf,office,html"),
    out: Optional[Path] = typer.Option(None, help="Optional plan output path."),
) -> None:
    app_config = load_config(config)
    app_config.ensure_directories()
    if not inventory_path.exists():
        raise typer.BadParameter(f"Inventory file not found: {inventory_path}")

    selected_types = _parse_library_types(types)
    records = _load_inventory_records(inventory_path)
    plan_rows = _build_library_plan(records, selected_types)
    output_path = out or _library_plan_path(app_config)
    append_jsonl(output_path, plan_rows)

    folder_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    unmapped = 0
    for row in plan_rows:
        kind_counts[row["library_kind"]] = kind_counts.get(row["library_kind"], 0) + 1
        folder_key = f"{row['library_kind']}/{row['domain']}/{row['topic_path']}"
        folder_counts[folder_key] = folder_counts.get(folder_key, 0) + 1
        if row["topic_path"].startswith("_unsorted") or row["topic_path"] == "_unsorted":
            unmapped += 1

    table = Table(title="Library Plan")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Planned records", str(len(plan_rows)))
    for kind, count in sorted(kind_counts.items()):
        table.add_row(kind, str(count))
    table.add_row("Folders", str(len(folder_counts)))
    table.add_row("Unsorted", str(unmapped))
    table.add_row("Output", str(output_path))
    console.print(table)

    preview = Table(title="Largest folders")
    preview.add_column("Folder")
    preview.add_column("Count")
    for folder, count in sorted(folder_counts.items(), key=lambda item: item[1], reverse=True)[:15]:
        preview.add_row(folder, str(count))
    console.print(preview)


@app.command("extract-tier-a")
def extract_tier_a(
    config: Optional[Path] = typer.Option(None, help="Path to config YAML."),
    library_path: Path = typer.Option(
        Path("data/manifests/pdf_library.jsonl"),
        help="Library manifest.",
    ),
    resume: bool = typer.Option(True, help="Skip rows with existing non-empty text."),
) -> None:
    """Extract text for all Tier A assets (PDF OCR, rendered PDF, office)."""
    from scraper.extract_tier_a_text import run_tier_a_extraction

    app_config = load_config(config)
    run_tier_a_extraction(
        app_config=app_config,
        library_path=library_path,
        resume=resume,
    )


@app.command("filter-corpus")
def filter_corpus(
    config: Optional[Path] = typer.Option(None, help="Path to config YAML."),
    library_path: Path = typer.Option(
        Path("data/manifests/pdf_library.jsonl"),
        help="PDF library manifest.",
    ),
    tier_text_path: Path = typer.Option(
        Path("data/manifests/farm_corpus_text.jsonl"),
        help="Farm corpus text manifest (Tier A + curated Tier B).",
    ),
) -> None:
    """Apply Tier A filters, boilerplate stripping, and write quality report (CAI-014–017, 020)."""
    app_config = load_config(config)
    app_config.ensure_directories()
    report = run_corpus_filter(
        app_config=app_config,
        library_path=library_path,
        tier_text_path=tier_text_path,
    )
    table = Table(title="Corpus Filter")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Accepted", str(report["filter_summary"]["accepted"]))
    for tier, count in sorted(report["filter_summary"].get("accepted_by_farm_ai_tier", {}).items()):
        table.add_row(f"  tier {tier}", str(count))
    for kind, count in sorted(report["filter_summary"].get("accepted_by_library_kind", {}).items()):
        table.add_row(f"  {kind}", str(count))
    table.add_row("Rejected", str(report["filter_summary"]["rejected"]))
    for reason, count in sorted(report["filter_summary"]["rejected_by_reason"].items()):
        table.add_row(f"  {reason}", str(count))
    table.add_row(
        "Extraction baseline",
        f"{report['extraction_baseline']['extracted']} extracted / "
        f"{report['extraction_baseline']['empty']} empty",
    )
    console.print(table)


if __name__ == "__main__":
    app()
