from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from scraper.utils import append_jsonl, write_json


class DocumentManifestRecord(BaseModel):
    source_url: str
    source_type: str
    title: str | None = None
    local_raw_path: str | None = None
    local_text_path: str | None = None
    local_pdf_path: str | None = None
    fetch_via: str | None = None
    http_status: int | None = None
    content_hash: str | None = None
    sitemap_origin: str | None = None
    discovered_from: str | None = None
    topic_path: str | None = None
    library_kind: str | None = None
    fetched_at: str
    error: str | None = None


class SitemapInventoryRecord(BaseModel):
    url: str
    normalized_url: str
    source_type: str
    sitemap_origin: str
    discovered_from: str | None = None
    depth: int | None = None
    fetched: bool | None = None
    outlink_count: int | None = None
    error: str | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_manifest(path: Path, payload: object) -> None:
    write_json(path, payload)


def write_jsonl_manifest(path: Path, records: list[BaseModel]) -> None:
    append_jsonl(path, [record.model_dump() for record in records])
