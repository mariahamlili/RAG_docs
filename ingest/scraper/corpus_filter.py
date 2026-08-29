"""Pre-chunk corpus filtering for Tier A extracted text (CAI-014–017, 020)."""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from scraper.config import AppConfig
from scraper.farm_tiers import corpus_tier, index_key_for_tier, is_corpus_eligible, is_tier_a
from scraper.tier_a_text import text_output_path

REASON_TIER_EXCLUDED = "TIER_EXCLUDED"
REASON_EMPTY_EXTRACTION = "EMPTY_EXTRACTION"
REASON_LIKELY_NON_TEXT_ASSET = "LIKELY_NON_TEXT_ASSET"
REASON_NEAR_DUPLICATE = "NEAR_DUPLICATE"

CORPUS_LIBRARY_KINDS = ("source_pdf", "rendered_pdf", "office")

EMPTY_TOKEN_THRESHOLD = 50
UNTITLED_TOKEN_THRESHOLD = 100
NEAR_DUP_THRESHOLD = 0.9
NEAR_DUP_REVIEW_THRESHOLD = 0.85
BOILERPLATE_MIN_PAGES = 3
BOILERPLATE_LINE_MAX_LEN = 80
BOILERPLATE_LINE_MIN_PAGE_RATIO = 0.5

NAV_PHRASE_BLOCKLIST = (
    "skip to main content",
    "skip to navigation",
    "skip to content",
    "accessibility",
    "listen to this page",
    "australian government",
    "department of agriculture",
    "search this website",
    "breadcrumb",
    "share on",
    "print this page",
    "was this page helpful",
    "copyright",
    "freedom of information",
    "privacy policy",
    "disclaimer",
)


@dataclass
class RejectedRecord:
    doc_id: str
    source_url: str
    local_path: str | None
    local_text_path: str | None
    topic_path: str | None
    doc_title: str
    reason: str
    token_count: int
    kept_doc_id: str | None = None
    similarity: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source_url": self.source_url,
            "local_path": self.local_path,
            "local_text_path": self.local_text_path,
            "topic_path": self.topic_path,
            "doc_title": self.doc_title,
            "reason": self.reason,
            "token_count": self.token_count,
            "kept_doc_id": self.kept_doc_id,
            "similarity": self.similarity,
            "details": self.details,
        }


@dataclass
class AcceptedRecord:
    doc_id: str
    source_url: str
    local_path: str | None
    local_source_text_path: str
    local_clean_text_path: str
    topic_path: str | None
    doc_title: str
    token_count_raw: int
    token_count_clean: int
    page_count: int
    topic_breadcrumb: list[str]
    library_kind: str
    farm_ai_tier: str
    index_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source_url": self.source_url,
            "local_path": self.local_path,
            "local_source_text_path": self.local_source_text_path,
            "local_clean_text_path": self.local_clean_text_path,
            "topic_path": self.topic_path,
            "doc_title": self.doc_title,
            "token_count_raw": self.token_count_raw,
            "token_count_clean": self.token_count_clean,
            "page_count": self.page_count,
            "topic_breadcrumb": self.topic_breadcrumb,
            "library_kind": self.library_kind,
            "farm_ai_tier": self.farm_ai_tier,
            "index_key": self.index_key,
        }


def doc_id_for(row: dict[str, Any]) -> str:
    return row.get("content_hash") or row["source_url"]


def doc_title_for(row: dict[str, Any]) -> str:
    if row.get("title"):
        return str(row["title"])
    if row.get("doc_title"):
        return str(row["doc_title"])
    breadcrumb = row.get("topic_breadcrumb") or []
    if breadcrumb:
        return str(breadcrumb[-1])
    filename = row.get("filename") or Path(row.get("local_path", "untitled")).name
    stem = Path(filename).stem.replace("-", " ").replace("_", " ").strip()
    return stem.title() if stem else "Untitled document"


def is_untitled_title(title: str) -> bool:
    normalized = title.strip().lower()
    if normalized in {"", "untitled", "untitled document"}:
        return True
    return normalized.startswith("untitled ")


def token_count(text: str) -> int:
    return len(text.split())


def normalize_for_duplicate(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"\s+", " ", lowered)
    lowered = re.sub(r"[^a-z0-9 ]", "", lowered)
    return lowered.strip()


def text_similarity(left: str, right: str, *, max_chars: int = 12000) -> float:
    left_norm = normalize_for_duplicate(left[:max_chars])
    right_norm = normalize_for_duplicate(right[:max_chars])
    if not left_norm or not right_norm:
        return 0.0
    shorter, longer = sorted((len(left_norm), len(right_norm)))
    if shorter / longer < 0.75:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def split_pages(text: str) -> list[str]:
    return [page.strip() for page in text.split("\n\n") if page.strip()]


def _line_is_blocked(line: str) -> bool:
    lowered = line.strip().lower()
    if not lowered:
        return True
    return any(phrase in lowered for phrase in NAV_PHRASE_BLOCKLIST)


def strip_boilerplate(text: str) -> str:
    pages = split_pages(text)
    if len(pages) < BOILERPLATE_MIN_PAGES:
        return "\n\n".join(
            line
            for page in pages
            for line in page.splitlines()
            if not _line_is_blocked(line)
        ).strip()

    repeated_lines: Counter[str] = Counter()
    pages_lines: list[list[str]] = []
    for page in pages:
        lines = page.splitlines()
        pages_lines.append(lines)
        seen_on_page: set[str] = set()
        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) > BOILERPLATE_LINE_MAX_LEN:
                continue
            key = stripped.lower()
            if key not in seen_on_page:
                seen_on_page.add(key)
                repeated_lines[key] += 1

    min_pages = max(1, int(len(pages) * BOILERPLATE_LINE_MIN_PAGE_RATIO))
    drop_lines = {line for line, count in repeated_lines.items() if count >= min_pages}

    cleaned_pages: list[str] = []
    for lines in pages_lines:
        kept = [
            line
            for line in lines
            if line.strip().lower() not in drop_lines and not _line_is_blocked(line)
        ]
        if kept:
            cleaned_pages.append("\n".join(kept))
    return "\n\n".join(cleaned_pages).strip()


def clean_text_path_for(source_text_path: Path, output_dir: Path) -> Path:
    parts = source_text_path.parts
    if "text" in parts:
        idx = parts.index("text")
        relative = Path(*parts[idx + 1 :])
        if relative.parts and relative.parts[0] == "source":
            relative = Path(*relative.parts[1:])
    else:
        relative = Path(source_text_path.name)
    return output_dir / "text" / "clean" / relative


def text_path_for_library_row(row: dict[str, Any], output_dir: Path) -> Path | None:
    """Resolve on-disk text for a library row (source PDF, rendered HTML/PDF, office)."""
    local_text = row.get("local_text_path")
    if local_text:
        path = Path(local_text)
        if path.exists():
            return path
    try:
        candidate = text_output_path(row, output_dir)
    except ValueError:
        return None
    return candidate if candidate.exists() else None


def _reject(
    rejected: list[RejectedRecord],
    *,
    row: dict[str, Any],
    title: str,
    doc_id: str,
    topic_path: str,
    reason: str,
    token_count_value: int = 0,
    text_path: Path | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    rejected.append(
        RejectedRecord(
            doc_id=doc_id,
            source_url=row["source_url"],
            local_path=row.get("local_path"),
            local_text_path=str(text_path) if text_path else None,
            topic_path=topic_path,
            doc_title=title,
            reason=reason,
            token_count=token_count_value,
            details=details or {},
        )
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_corpus_filter(
    *,
    app_config: AppConfig,
    library_path: Path,
    tier_text_path: Path,
    rejected_path: Path | None = None,
    accepted_path: Path | None = None,
    report_json_path: Path | None = None,
    report_md_path: Path | None = None,
    empty_review_path: Path | None = None,
    near_dup_review_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = app_config.output_dir
    manifests = output_dir / "manifests"
    rejected_path = rejected_path or manifests / "rejected.jsonl"
    accepted_path = accepted_path or manifests / "corpus_accepted.jsonl"
    report_json_path = report_json_path or manifests / "extraction_quality_report.json"
    report_md_path = report_md_path or manifests / "extraction_quality_report.md"
    empty_review_path = empty_review_path or manifests / "empty_extractions_review.md"
    near_dup_review_path = near_dup_review_path or manifests / "near_duplicate_review_sample.jsonl"

    library_rows = load_jsonl(library_path)
    tier_rows = {
        row["source_url"]: row
        for row in load_jsonl(tier_text_path)
        if row.get("source_url")
    }

    corpus_rows = [
        row
        for row in library_rows
        if row.get("library_kind") in CORPUS_LIBRARY_KINDS
        and row.get("status") in {"fetched", "skipped"}
    ]

    rejected: list[RejectedRecord] = []
    candidates: list[dict[str, Any]] = []

    for row in corpus_rows:
        topic_path = row.get("topic_path") or ""
        title = doc_title_for(row)
        doc_id = doc_id_for(row)
        library_kind = str(row.get("library_kind") or "")

        if not is_corpus_eligible(topic_path):
            _reject(
                rejected,
                row=row,
                title=title,
                doc_id=doc_id,
                topic_path=topic_path,
                reason=REASON_TIER_EXCLUDED,
                details={"tier": "not_eligible", "library_kind": library_kind},
            )
            continue

        farm_ai_tier = corpus_tier(topic_path) or "A"
        index_key = index_key_for_tier(farm_ai_tier)

        tier_row = tier_rows.get(row["source_url"])
        if not tier_row:
            text_path = text_path_for_library_row(row, output_dir)
            if not text_path:
                _reject(
                    rejected,
                    row=row,
                    title=title,
                    doc_id=doc_id,
                    topic_path=topic_path,
                    reason=REASON_EMPTY_EXTRACTION,
                    details={"note": "missing_from_farm_corpus_text", "library_kind": library_kind},
                )
                continue
        else:
            text_path = Path(tier_row.get("local_text_path") or "")
            if tier_row.get("text_status") == "failed" or not text_path.exists():
                fallback = text_path_for_library_row(row, output_dir)
                if fallback:
                    text_path = fallback
                else:
                    _reject(
                        rejected,
                        row=row,
                        title=title,
                        doc_id=doc_id,
                        topic_path=topic_path,
                        reason=REASON_EMPTY_EXTRACTION,
                        text_path=text_path if text_path else None,
                        details={
                            "text_status": tier_row.get("text_status", "missing_file"),
                            "library_kind": library_kind,
                        },
                    )
                    continue

        raw_text = text_path.read_text(encoding="utf-8", errors="replace")
        tokens = token_count(raw_text)

        if tokens < EMPTY_TOKEN_THRESHOLD:
            _reject(
                rejected,
                row=row,
                title=title,
                doc_id=doc_id,
                topic_path=topic_path,
                reason=REASON_EMPTY_EXTRACTION,
                token_count_value=tokens,
                text_path=text_path,
                details={
                    "library_kind": library_kind,
                    "text_status": tier_row.get("text_status") if tier_row else "html_extract",
                },
            )
            continue

        if is_untitled_title(title) and tokens < UNTITLED_TOKEN_THRESHOLD:
            _reject(
                rejected,
                row=row,
                title=title,
                doc_id=doc_id,
                topic_path=topic_path,
                reason=REASON_LIKELY_NON_TEXT_ASSET,
                token_count_value=tokens,
                text_path=text_path,
                details={"library_kind": library_kind},
            )
            continue

        candidates.append(
            {
                "row": row,
                "tier_row": tier_row,
                "doc_id": doc_id,
                "title": title,
                "text_path": text_path,
                "raw_text": raw_text,
                "tokens": tokens,
                "topic_root": (topic_path or "").split("/")[0],
                "library_kind": library_kind,
                "farm_ai_tier": farm_ai_tier,
                "index_key": index_key,
            }
        )

    # Near-duplicate detection: keep longer/higher-token document.
    candidates.sort(key=lambda item: item["tokens"], reverse=True)
    accepted_candidates: list[dict[str, Any]] = []
    near_dup_pairs: list[dict[str, Any]] = []
    accepted_by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for candidate in candidates:
        duplicate_of: dict[str, Any] | None = None
        best_similarity = 0.0
        topic_peers = accepted_by_topic.get(candidate["topic_root"], [])
        for kept in topic_peers:
            if (
                min(candidate["tokens"], kept["tokens"])
                / max(candidate["tokens"], kept["tokens"])
                < 0.75
            ):
                continue
            similarity = text_similarity(candidate["raw_text"], kept["raw_text"])
            if similarity >= NEAR_DUP_REVIEW_THRESHOLD:
                near_dup_pairs.append(
                    {
                        "doc_id_a": candidate["doc_id"],
                        "doc_id_b": kept["doc_id"],
                        "title_a": candidate["title"],
                        "title_b": kept["title"],
                        "similarity": round(similarity, 4),
                        "source_url_a": candidate["row"]["source_url"],
                        "source_url_b": kept["row"]["source_url"],
                        "local_path_a": candidate["row"].get("local_path"),
                        "local_path_b": kept["row"].get("local_path"),
                        "auto_rejected": similarity >= NEAR_DUP_THRESHOLD,
                    }
                )
            if similarity > best_similarity:
                best_similarity = similarity
                if similarity >= NEAR_DUP_THRESHOLD:
                    duplicate_of = kept

        if duplicate_of:
            rejected.append(
                RejectedRecord(
                    doc_id=candidate["doc_id"],
                    source_url=candidate["row"]["source_url"],
                    local_path=candidate["row"].get("local_path"),
                    local_text_path=str(candidate["text_path"]),
                    topic_path=candidate["row"].get("topic_path"),
                    doc_title=candidate["title"],
                    reason=REASON_NEAR_DUPLICATE,
                    token_count=candidate["tokens"],
                    kept_doc_id=duplicate_of["doc_id"],
                    similarity=round(best_similarity, 4),
                    details={
                        "kept_source_url": duplicate_of["row"]["source_url"],
                        "kept_local_path": duplicate_of["row"].get("local_path"),
                    },
                )
            )
            continue

        accepted_candidates.append(candidate)
        accepted_by_topic[candidate["topic_root"]].append(candidate)

    accepted: list[AcceptedRecord] = []
    for candidate in accepted_candidates:
        cleaned = strip_boilerplate(candidate["raw_text"])
        clean_path = clean_text_path_for(candidate["text_path"], output_dir)
        clean_path.parent.mkdir(parents=True, exist_ok=True)
        clean_path.write_text(cleaned, encoding="utf-8")
        accepted.append(
            AcceptedRecord(
                doc_id=candidate["doc_id"],
                source_url=candidate["row"]["source_url"],
                local_path=candidate["row"].get("local_path"),
                local_source_text_path=str(candidate["text_path"]),
                local_clean_text_path=str(clean_path),
                topic_path=candidate["row"].get("topic_path"),
                doc_title=candidate["title"],
                token_count_raw=candidate["tokens"],
                token_count_clean=token_count(cleaned),
                page_count=len(split_pages(candidate["raw_text"])),
                topic_breadcrumb=list(candidate["row"].get("topic_breadcrumb") or []),
                library_kind=candidate["library_kind"],
                farm_ai_tier=candidate["farm_ai_tier"],
                index_key=candidate["index_key"],
            )
        )

    write_jsonl(rejected_path, [row.to_dict() for row in rejected])
    write_jsonl(accepted_path, [row.to_dict() for row in accepted])

    reason_counts = Counter(row.reason for row in rejected)
    topic_counts = Counter((row.topic_path or "").split("/")[0] for row in accepted)
    accepted_kind_counts = Counter(row.library_kind for row in accepted)
    accepted_tier_counts = Counter(row.farm_ai_tier for row in accepted)
    accepted_index_counts = Counter(row.index_key for row in accepted)
    token_values = [row.token_count_clean for row in accepted]

    extraction_empty = sum(
        1 for row in tier_rows.values() if row.get("text_status") == "empty"
    )
    extraction_extracted = sum(
        1 for row in tier_rows.values() if row.get("text_status") == "extracted"
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "library_path": str(library_path),
            "tier_text_path": str(tier_text_path),
        },
        "outputs": {
            "rejected_path": str(rejected_path),
            "accepted_path": str(accepted_path),
            "empty_review_path": str(empty_review_path),
            "near_dup_review_path": str(near_dup_review_path),
        },
        "extraction_baseline": {
            "corpus_targets": len(tier_rows),
            "extracted": extraction_extracted,
            "empty": extraction_empty,
            "failed": sum(1 for row in tier_rows.values() if row.get("text_status") == "failed"),
        },
        "filter_summary": {
            "library_rows_scanned": len(corpus_rows),
            "library_kinds": list(CORPUS_LIBRARY_KINDS),
            "corpus_eligible_tier_a": sum(
                1
                for row in corpus_rows
                if corpus_tier(row.get("topic_path") or "") == "A"
            ),
            "corpus_eligible_tier_b": sum(
                1
                for row in corpus_rows
                if corpus_tier(row.get("topic_path") or "") == "B"
            ),
            "accepted": len(accepted),
            "accepted_by_library_kind": dict(sorted(accepted_kind_counts.items())),
            "accepted_by_farm_ai_tier": dict(sorted(accepted_tier_counts.items())),
            "accepted_by_index_key": dict(sorted(accepted_index_counts.items())),
            "rejected": len(rejected),
            "rejected_by_reason": dict(reason_counts),
        },
        "accepted_token_stats": {
            "min": min(token_values) if token_values else 0,
            "max": max(token_values) if token_values else 0,
            "mean": round(statistics.mean(token_values), 1) if token_values else 0,
            "median": round(statistics.median(token_values), 1) if token_values else 0,
        },
        "accepted_by_topic_root": dict(sorted(topic_counts.items(), key=lambda item: (-item[1], item[0]))),
    }

    report_json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_report_markdown(report_md_path, report, accepted, rejected)
    _write_empty_review(empty_review_path, tier_rows)
    _write_near_dup_sample(near_dup_review_path, near_dup_pairs)

    return report


def _write_report_markdown(
    path: Path,
    report: dict[str, Any],
    accepted: list[AcceptedRecord],
    rejected: list[RejectedRecord],
) -> None:
    lines = [
        "# Extraction quality report",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Extraction baseline (Tier A PDFs)",
        "",
        f"| Metric | Count |",
        f"|---|---|",
    ]
    baseline = report["extraction_baseline"]
    for key, value in baseline.items():
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## Filter summary",
            "",
            f"| Metric | Count |",
            f"|---|---|",
        ]
    )
    summary = report["filter_summary"]
    lines.append(f"| accepted (clean corpus) | {summary['accepted']} |")
    lines.append(f"| rejected | {summary['rejected']} |")
    for reason, count in sorted(summary["rejected_by_reason"].items()):
        lines.append(f"| rejected: {reason} | {count} |")

    lines.extend(
        [
            "",
            "## Accepted token stats (after boilerplate strip)",
            "",
            json.dumps(report["accepted_token_stats"], indent=2),
            "",
            "## Top topic roots (accepted)",
            "",
        ]
    )
    for topic, count in list(report["accepted_by_topic_root"].items())[:20]:
        lines.append(f"- `{topic}`: {count}")

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Accepted manifest: `{report['outputs']['accepted_path']}`",
            f"- Rejected manifest: `{report['outputs']['rejected_path']}`",
            f"- Empty extraction review (CAI-018): `{report['outputs']['empty_review_path']}`",
            f"- Near-duplicate sample (CAI-019): `{report['outputs']['near_dup_review_path']}`",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _markdown_file_link(path_str: str, *, from_dir: Path, label: str | None = None) -> str:
    if not path_str:
        return ""
    path = Path(path_str)
    display = label or path.name
    parts = path.parts
    if len(parts) >= 2 and parts[0] == "data":
        href = str(Path("..") / Path(*parts[1:])).replace(" ", "%20")
    else:
        try:
            href = str(path.resolve().relative_to(from_dir.resolve())).replace(" ", "%20")
        except ValueError:
            href = path_str.replace(" ", "%20")
    return f"[{display}]({href})"


def _write_empty_review(path: Path, tier_rows: dict[str, dict[str, Any]]) -> None:
    empties = [row for row in tier_rows.values() if row.get("text_status") == "empty"]
    from_dir = path.parent
    lines = [
        "# Tier A empty extractions — manual review (CAI-018)",
        "",
        f"**Count:** {len(empties)} documents",
        "",
        "Classify each row as `ocr_recoverable` or `genuinely_non_textual`.",
        "",
        "Links: **local** opens the file in this repo; **web** opens the original on agriculture.gov.au.",
        "",
        "| # | PDF (local · web) | Text | Tokens | Review | Notes |",
        "|---|---|---|---:|---|---|",
    ]
    for index, row in enumerate(sorted(empties, key=lambda r: r.get("local_path", "")), start=1):
        text_path = row.get("local_text_path") or ""
        pdf_path = row.get("local_path") or ""
        filename = Path(pdf_path).name if pdf_path else ""
        source_url = row.get("source_url") or ""
        tokens = row.get("text_chars", 0)
        local_pdf = _markdown_file_link(pdf_path, from_dir=from_dir, label=filename)
        web_pdf = f"[web]({source_url})" if source_url else ""
        pdf_links = f"{local_pdf} · {web_pdf}" if web_pdf else local_pdf
        text_link = _markdown_file_link(text_path, from_dir=from_dir, label="text")
        lines.append(
            f"| {index} | {pdf_links} | {text_link} | {tokens} | _pending_ | |"
        )
    lines.extend(
        [
            "",
            "## How to review",
            "",
            "1. Open the PDF in Preview or a browser.",
            "2. If you see readable text as images/scans → mark `ocr_recoverable`.",
            "3. If the PDF is blank, corrupted, or image-only with no useful text → `genuinely_non_textual`.",
            "4. Save conclusions in this file or `data/manifests/empty_extractions_review.jsonl`.",
            "",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_near_dup_sample(path: Path, pairs: list[dict[str, Any]]) -> None:
    # Prioritise high-similarity pairs not auto-rejected, then auto-rejected, cap at 30.
    pairs_sorted = sorted(pairs, key=lambda p: (p["similarity"], p["auto_rejected"]), reverse=True)
    sample = pairs_sorted[:30]
    write_jsonl(path, sample)
