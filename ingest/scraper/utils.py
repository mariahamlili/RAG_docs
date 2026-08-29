from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from slugify import slugify


def strip_tracking_params(query: str, ignored_prefixes: list[str]) -> str:
    if not query:
        return ""

    filtered_pairs = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        should_skip = any(
            key == prefix or key.startswith(prefix) for prefix in ignored_prefixes
        )
        if not should_skip:
            filtered_pairs.append((key, value))
    return urlencode(filtered_pairs, doseq=True)


def normalize_url(url: str, ignored_prefixes: list[str]) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    query = strip_tracking_params(parts.query, ignored_prefixes)
    return urlunsplit((scheme, netloc, path, query, ""))


def is_same_scope(root_url: str, candidate_url: str, follow_subdomains: bool) -> bool:
    root_parts = urlsplit(root_url)
    candidate_parts = urlsplit(candidate_url)
    if root_parts.scheme != candidate_parts.scheme:
        return False
    if follow_subdomains:
        return candidate_parts.netloc == root_parts.netloc or candidate_parts.netloc.endswith(
            f".{root_parts.netloc}"
        )
    return candidate_parts.netloc == root_parts.netloc


def resolve_url(root_url: str, url: str) -> str:
    return urljoin(root_url, url)


def extract_internal_links(
    html: str,
    page_url: str,
    root_url: str,
    ignored_prefixes: list[str],
    follow_subdomains: bool,
) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    discovered: list[str] = []
    seen = set()

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        if not href:
            continue
        lowered_href = href.lower()
        if lowered_href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        resolved = resolve_url(page_url, href)
        normalized = normalize_url(resolved, ignored_prefixes)
        if not is_same_scope(root_url, normalized, follow_subdomains):
            continue
        if normalized in seen:
            continue

        seen.add(normalized)
        discovered.append(normalized)

    return discovered


def slug_from_url(url: str) -> str:
    parts = urlsplit(url)
    slug_base = f"{parts.netloc}{parts.path}"
    if parts.query:
        slug_base = f"{slug_base}-{parts.query}"
    slug = slugify(slug_base, separator="-")
    return slug or "document"


def extension_from_url(url: str) -> str:
    path = urlsplit(url).path
    suffix = Path(path).suffix.lower()
    return suffix or ".html"


def path_from_url(url: str, base_dir: Path, extension: str) -> Path:
    """Map a URL to a mirrored folder hierarchy under base_dir.

    Assets served from /sites/default/files/documents/ are flattened to
    domain/documents/<filename> so the deep CMS path doesn't pollute the tree.
    """
    parts = urlsplit(url)
    domain = parts.netloc.lower().lstrip("www.")
    raw_path = parts.path.strip("/")
    segments = [s for s in raw_path.split("/") if s]

    if not segments:
        return base_dir / domain / f"index{extension}"

    # flatten Drupal file-server paths to documents/<filename>
    if raw_path.startswith("sites/default/files/"):
        filename = segments[-1]
        stem = Path(filename).stem if Path(filename).suffix else filename
        return base_dir / domain / "documents" / f"{stem}{extension}"

    *folders, filename = segments
    stem = Path(filename).stem if Path(filename).suffix else filename
    if folders:
        return base_dir / domain / Path(*folders) / f"{stem}{extension}"
    return base_dir / domain / f"{stem}{extension}"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def append_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
