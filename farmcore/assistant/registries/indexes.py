from __future__ import annotations

from dataclasses import dataclass

REGISTRY_VERSION = "indexes-v0"


@dataclass(frozen=True)
class IndexEntry:
    index_key: str
    description: str
    tier: str | None
    requires_snapshot: bool


_REGISTRY: dict[str, IndexEntry] = {
    "gov_tier_a": IndexEntry(
        index_key="gov_tier_a",
        description="Default government corpus (Tier A)",
        tier="A",
        requires_snapshot=True,
    ),
    "gov_tier_b": IndexEntry(
        index_key="gov_tier_b",
        description="Government fallback corpus (Tier B)",
        tier="B",
        requires_snapshot=True,
    ),
    "tenant_doc": IndexEntry(
        index_key="tenant_doc",
        description="Farm-uploaded documents",
        tier=None,
        requires_snapshot=False,
    ),
}


def get_index(key: str) -> IndexEntry:
    return _REGISTRY[key]


def all_indexes() -> dict[str, IndexEntry]:
    return dict(_REGISTRY)


def registry_version() -> str:
    return REGISTRY_VERSION
