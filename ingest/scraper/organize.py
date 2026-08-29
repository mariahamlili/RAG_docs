from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from slugify import slugify

# Longest-prefix-first curated renames of referring-page / page path segments.
TOPIC_MAP: dict[tuple[str, ...], tuple[str, ...]] = {
    ("agriculture-land", "farm-food-drought", "drought"): ("drought-and-farm-support",),
    ("agriculture-land", "farm-food-drought", "ag-vet-chemicals"): ("agvet-chemicals",),
    ("agriculture-land", "farm-food-drought", "biotechnology"): ("biotechnology",),
    ("agriculture-land", "farm-food-drought", "food"): ("food-policy",),
    ("agriculture-land", "farm-food-drought", "crops"): ("crops",),
    ("agriculture-land", "farm-food-drought", "climatechange"): ("climate-change",),
    ("agriculture-land", "farm-food-drought", "levies"): ("levies",),
    ("agriculture-land", "farm-food-drought", "ag2030"): ("strategy-and-plans", "ag2030"),
    ("agriculture-land", "farm-food-drought", "mouse-infestation"): ("crops", "mouse-infestation"),
    ("agriculture-land", "animal", "aquatic"): ("animal-health", "aquatic"),
    ("agriculture-land", "animal", "health"): ("animal-health", "terrestrial"),
    ("agriculture-land", "animal", "welfare"): ("animal-welfare",),
    ("agriculture-land", "animal-welfare"): ("animal-welfare",),
    ("agriculture-land", "forestry"): ("forestry",),
    ("agriculture-land", "fisheries"): ("fisheries",),
    ("agriculture-land", "plant"): ("plant-health",),
    ("ag-farm-food", "drought"): ("drought-and-farm-support",),
    ("ag-farm-food", "ag-vet-chemicals"): ("agvet-chemicals",),
    ("ag-farm-food", "biotechnology"): ("biotechnology",),
    ("ag-farm-food", "food"): ("food-policy",),
    ("ag-farm-food", "crops"): ("crops",),
    ("ag-farm-food", "agriculture-white-paper"): ("strategy-and-plans", "agriculture-white-paper"),
    ("animal", "health"): ("animal-health", "terrestrial"),
    ("animal", "aquatic"): ("animal-health", "aquatic"),
    ("animal", "welfare"): ("animal-welfare",),
    ("animal", "animal-pests-and-diseases"): ("animal-health", "pests-and-diseases"),
    ("about", "fees"): ("corporate", "fees-and-cost-recovery"),
    ("about", "reporting"): ("corporate", "reporting"),
    ("about", "assistance-grants-tenders"): ("corporate", "grants-and-tenders"),
    ("about", "jobs"): ("corporate", "jobs"),
    ("about", "who-we-are"): ("corporate", "who-we-are"),
    ("about", "what-we-do"): ("corporate", "what-we-do"),
    ("about", "publications"): ("corporate", "publications"),
    ("about", "news"): ("corporate", "news"),
    ("about", "commitment"): ("corporate", "governance"),
    ("about", "payments"): ("corporate", "payments"),
    ("about", "contact"): ("corporate", "contact"),
    ("about", "contactus"): ("corporate", "contact"),
    ("bmsb",): ("biosecurity", "brown-marmorated-stink-bug"),
    ("biosecurity-trade",): ("biosecurity-trade",),
    ("biosecurity",): ("biosecurity",),
    ("pests-diseases-weeds",): ("biosecurity", "pests-diseases-weeds"),
    ("campaigns", "birdflu"): ("biosecurity", "avian-influenza"),
    ("campaigns",): ("campaigns",),
    ("abares",): ("abares",),
    ("climate-change",): ("climate-change",),
    ("forestry",): ("forestry",),
    ("plant",): ("plant-health",),
    ("import",): ("biosecurity-trade", "import"),
    ("export",): ("biosecurity-trade", "export"),
    ("travelling",): ("biosecurity-trade", "travelling"),
    ("cats-dogs",): ("biosecurity-trade", "cats-dogs"),
    ("market-access-trade",): ("biosecurity-trade", "market-access-trade"),
    ("fees",): ("corporate", "fees-and-cost-recovery"),
    ("current-job-vacancies",): ("corporate", "jobs"),
    ("science-research",): ("science-research",),
    ("online-services",): ("online-services",),
    ("publications",): ("corporate", "publications"),
    ("haveyoursay",): ("consultation",),
    ("coronavirus",): ("biosecurity", "coronavirus"),
    ("media",): ("corporate", "media"),
    ("contact",): ("corporate", "contact"),
    ("forms",): ("corporate", "forms"),
}

ACRONYMS: dict[str, str] = {
    "fmd": "farm-management-deposits",
    "rfcs": "rural-financial-counselling-service",
    "ric": "regional-investment-corporation",
    "mel": "monitoring-evaluation-learning",
    "aaws": "australian-animal-welfare-strategy",
    "asel": "australian-standards-for-export-livestock",
    "ahc": "animal-health-committee",
    "cris": "cost-recovery-implementation-statement",
    "pbs": "portfolio-budget-statements",
    "paes": "portfolio-additional-estimates-statements",
    "foi": "freedom-of-information",
    "rdr": "regional-drought-resilience",
}

_MONTHS = {name.lower(): f"{idx:02d}" for idx, name in enumerate(calendar.month_name) if name}
_MONTHS.update({name.lower(): f"{idx:02d}" for idx, name in enumerate(calendar.month_abbr) if name})

_DRUPAL_REV = re.compile(r"^(?P<stem>.+)_(?P<rev>\d+)$")
_FMD_STATS_A = re.compile(
    r"^fmd-statistics-(?P<month>[a-z]+)(?P<year>\d{4})$", re.IGNORECASE
)
_FMD_STATS_B = re.compile(
    r"^(?P<month>[a-z]+)-(?P<year>\d{4})-fmd-statistics$", re.IGNORECASE
)
_FMD_STATS_C = re.compile(
    r"^fmd-statistics-(?P<year>\d{4})-(?P<month>[a-z]+)$", re.IGNORECASE
)

MAX_TOPIC_DEPTH = 4
MAX_STEM_LEN = 80
COLLAPSE_MIN_FILES = 3


@dataclass(frozen=True)
class LibraryDestination:
    library_kind: str  # source_pdf | rendered_pdf | office
    domain: str
    topic_parts: tuple[str, ...]
    filename: str
    relative_path: str

    @property
    def topic_path(self) -> str:
        return "/".join(self.topic_parts)


def _path_segments(url: str) -> tuple[str, ...]:
    path = urlsplit(url).path.strip("/")
    if not path:
        return ()
    return tuple(unquote(segment) for segment in path.split("/") if segment)


def _domain_from_url(url: str) -> str:
    return urlsplit(url).netloc.lower().lstrip("www.") or "unknown"


def _slug_segment(segment: str) -> str:
    expanded = ACRONYMS.get(segment.lower(), segment)
    slug = slugify(expanded, separator="-")
    return slug or "item"


def _apply_topic_map(segments: tuple[str, ...]) -> tuple[str, ...]:
    if not segments:
        return ("_unsorted",)
    normalized = tuple(segment.lower() for segment in segments)
    best_key: tuple[str, ...] | None = None
    for key in TOPIC_MAP:
        if normalized[: len(key)] == key and (best_key is None or len(key) > len(best_key)):
            best_key = key
    if best_key is None:
        return tuple(_slug_segment(segment) for segment in normalized)
    mapped = TOPIC_MAP[best_key]
    remainder = normalized[len(best_key) :]
    return mapped + tuple(_slug_segment(segment) for segment in remainder)


def _site_collection_fallback(source_url: str) -> tuple[str, ...] | None:
    segments = _path_segments(source_url)
    lowered = tuple(segment.lower() for segment in segments)
    marker = ("sites", "default", "files", "sitecollectiondocuments")
    if len(lowered) > len(marker) and lowered[: len(marker)] == marker:
        topical = lowered[len(marker) : -1]  # drop filename
        if topical:
            return tuple(_slug_segment(segment) for segment in topical)
    return None


def topic_path_for(
    source_url: str,
    *,
    source_type: str,
    discovered_from: str | None = None,
) -> tuple[str, ...]:
    """Return topic folders under the domain (no domain, no filename)."""
    if source_type == "html":
        segments = _path_segments(source_url)
    else:
        segments = _path_segments(discovered_from or "")
        if not segments:
            fallback = _site_collection_fallback(source_url)
            if fallback:
                return fallback[:MAX_TOPIC_DEPTH]
            return ("_unsorted",)

    mapped = _apply_topic_map(segments)
    if mapped == ("_unsorted",) or (
        source_type != "html" and not segments and mapped == ("_unsorted",)
    ):
        fallback = _site_collection_fallback(source_url)
        if fallback:
            return fallback[:MAX_TOPIC_DEPTH]
    return mapped[:MAX_TOPIC_DEPTH]


def _normalize_fmd_stats_stem(stem: str) -> str:
    for pattern in (_FMD_STATS_A, _FMD_STATS_B, _FMD_STATS_C):
        match = pattern.match(stem)
        if not match:
            continue
        month_key = match.group("month").lower()
        month_num = _MONTHS.get(month_key)
        year = match.group("year")
        if month_num:
            return f"fmd-statistics-{year}-{month_num}"
    return stem


def _prepare_stem(raw_stem: str) -> str:
    decoded = unquote(raw_stem).strip()
    decoded = decoded.replace("_", "-")
    slug = slugify(decoded, separator="-") or "document"
    slug = _normalize_fmd_stats_stem(slug)

    rev_match = _DRUPAL_REV.match(slug)
    if rev_match and rev_match.group("stem"):
        slug = f"{rev_match.group('stem')}-r{rev_match.group('rev')}"

    return slug


def filename_for(
    source_url: str,
    *,
    extension: str,
    content_hash: str | None = None,
    taken: set[str] | None = None,
    topic_leaf: str | None = None,
) -> str:
    """Build a collision-safe filename with the given extension (including dot)."""
    taken = taken if taken is not None else set()
    path_name = Path(unquote(urlsplit(source_url).path)).name
    raw_stem = Path(path_name).stem if path_name else "document"
    if not Path(path_name).suffix and extension:
        raw_stem = path_name or "document"

    stem = _prepare_stem(raw_stem)
    if stem.isdigit() and topic_leaf:
        stem = f"{topic_leaf}-{stem}"

    hash_prefix = (content_hash or "00000000")[:8]
    if len(stem) > MAX_STEM_LEN:
        stem = f"{stem[:MAX_STEM_LEN].rstrip('-')}-{hash_prefix}"

    candidate = f"{stem}{extension.lower()}"
    if candidate not in taken:
        taken.add(candidate)
        return candidate

    candidate = f"{stem}-{hash_prefix}{extension.lower()}"
    suffix = 2
    while candidate in taken:
        candidate = f"{stem}-{hash_prefix}-{suffix}{extension.lower()}"
        suffix += 1
    taken.add(candidate)
    return candidate


def collapse_small_folders(
    assignments: list[tuple[tuple[str, ...], str]],
    *,
    min_files: int = COLLAPSE_MIN_FILES,
) -> dict[str, tuple[str, ...]]:
    """Map source_url -> collapsed topic parts.

    `assignments` is a list of (topic_parts, source_url). Folders with fewer than
    `min_files` files are merged into their parent until stable.
    """
    current: dict[str, tuple[str, ...]] = {
        source_url: topic_parts for topic_parts, source_url in assignments
    }

    changed = True
    while changed:
        changed = False
        counts: dict[tuple[str, ...], int] = {}
        for topic_parts in current.values():
            counts[topic_parts] = counts.get(topic_parts, 0) + 1

        for source_url, topic_parts in list(current.items()):
            if len(topic_parts) <= 1:
                continue
            if counts.get(topic_parts, 0) >= min_files:
                continue
            current[source_url] = topic_parts[:-1]
            changed = True

    return current


def library_kind_for(source_type: str) -> str:
    if source_type == "html":
        return "rendered_pdf"
    if source_type == "asset:pdf":
        return "source_pdf"
    if source_type.startswith("asset:"):
        return "office"
    return "office"


def extension_for(source_type: str, source_url: str) -> str:
    if source_type == "html":
        return ".pdf"
    if source_type.startswith("asset:"):
        return f".{source_type.split(':', 1)[1]}"
    suffix = Path(urlsplit(source_url).path).suffix.lower()
    return suffix or ".bin"


def destination_root(library_kind: str, output_dir: Path) -> Path:
    if library_kind == "source_pdf":
        return output_dir / "pdf" / "source"
    if library_kind == "rendered_pdf":
        return output_dir / "pdf" / "rendered"
    return output_dir / "office"


def build_destination(
    *,
    source_url: str,
    source_type: str,
    discovered_from: str | None,
    topic_parts: tuple[str, ...],
    taken_in_folder: set[str],
    content_hash: str | None = None,
) -> LibraryDestination:
    kind = library_kind_for(source_type)
    domain = _domain_from_url(source_url if source_type == "html" else (discovered_from or source_url))
    if source_type != "html":
        domain = _domain_from_url(source_url)
    extension = extension_for(source_type, source_url)
    topic_leaf = topic_parts[-1] if topic_parts else None
    filename = filename_for(
        source_url,
        extension=extension,
        content_hash=content_hash,
        taken=taken_in_folder,
        topic_leaf=topic_leaf,
    )
    relative = "/".join((domain, *topic_parts, filename))
    return LibraryDestination(
        library_kind=kind,
        domain=domain,
        topic_parts=topic_parts,
        filename=filename,
        relative_path=relative,
    )


def breadcrumb_for(topic_parts: tuple[str, ...]) -> list[str]:
    return [part.replace("-", " ").title() for part in topic_parts]
