"""Farm AI corpus tier classification (Tier A default, curated Tier B promote)."""

from __future__ import annotations

import re

TIER_A_PREFIXES = [
    "drought-and-farm-support",
    "animal-health",
    "animal-welfare",
    "crops",
    "plant-health",
    "agvet-chemicals",
    "climate-change",
    "biosecurity",
    "biosecurity-trade/pests-diseases-weeds",
    "biotechnology",
    "strategy-and-plans",
    "agriculture-land",
    "abares/research-topics",
    "abares/products",
]

TIER_B_PROMOTE_CHECKS: tuple[tuple[str, str], ...] = (
    ("export_livestock_meat", r"controlled-goods/(live-animals|meat)"),
    ("export_dairy_eggs", r"controlled-goods/(dairy|eggs)"),
    ("export_plants", r"controlled-goods/plants"),
    ("export_organic", r"organic-bio-dynamic"),
    ("export_other", r"controlled-goods/non-prescribed"),
    ("market_access", r"market-access-trade"),
    ("nrs", r"food-policy/nrs"),
    ("food_policy", r"^food-policy"),
    ("import_ag", r"import/goods/(food|plant-products|biological)"),
    ("export_general", r"biosecurity-trade/export"),
)

TIER_B_EXCLUDED_RE = re.compile(r"nexdoc|exdoc|certification", re.I)


def _matches(path: str, prefixes: list[str]) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)


def is_tier_a(topic_path: str) -> bool:
    return _matches(topic_path or "", TIER_A_PREFIXES)


def tier_b_promote_bucket(topic_path: str) -> str | None:
    """Return promote bucket name for curated Tier B, or None."""
    path = topic_path or ""
    if is_tier_a(path):
        return None

    lowered = path.lower()
    if "cats-dogs" in lowered or "travelling" in lowered:
        return None
    if lowered.startswith("levies"):
        return None
    if "/arrival/" in lowered or lowered.endswith("/arrival"):
        return None
    if lowered.startswith("fisheries") or lowered.startswith("forestry"):
        return None
    if "controlled-goods/fish" in lowered:
        return None
    if TIER_B_EXCLUDED_RE.search(lowered):
        return None

    for bucket, pattern in TIER_B_PROMOTE_CHECKS:
        if re.search(pattern, lowered):
            return bucket
    return None


def is_tier_b_promote(topic_path: str) -> bool:
    return tier_b_promote_bucket(topic_path) is not None


def corpus_tier(topic_path: str) -> str | None:
    if is_tier_a(topic_path):
        return "A"
    if is_tier_b_promote(topic_path):
        return "B"
    return None


def is_corpus_eligible(topic_path: str) -> bool:
    return corpus_tier(topic_path) is not None


def index_key_for_tier(tier: str) -> str:
    if tier == "B":
        return "gov_tier_b"
    return "gov_tier_a"
