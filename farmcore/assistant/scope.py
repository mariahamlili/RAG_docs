from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

GOV_INDEX_KEYS = frozenset({"gov_tier_a", "gov_tier_b"})
TENANT_INDEX_KEY = "tenant_doc"


@dataclass(frozen=True)
class RetrievalScope:
    principal_user_id: UUID
    farm_id: UUID | None
    farm_role: Literal["owner", "worker"]
    logical_indexes: frozenset[str]
    doc_states: frozenset[str]
    allowed_document_ids: frozenset[UUID] | None
    snapshot_id: str | None
    as_of: datetime
    top_k: int

    def __post_init__(self) -> None:
        if not self.logical_indexes:
            raise ValueError("logical_indexes must not be empty")
        if self.top_k < 1:
            raise ValueError("top_k must be >= 1")
        if TENANT_INDEX_KEY in self.logical_indexes and self.logical_indexes & GOV_INDEX_KEYS:
            raise ValueError("tenant_doc cannot be mixed with gov_* indexes in one scope")
        if TENANT_INDEX_KEY in self.logical_indexes and self.farm_id is None:
            raise ValueError("tenant_doc scope requires farm_id")
        if self.logical_indexes & GOV_INDEX_KEYS and self.farm_id is not None:
            # Gov-only retrieval for public corpus uses farm_id=None.
            raise ValueError("gov_* scopes must use farm_id=None")
        if self.farm_role == "worker" and TENANT_INDEX_KEY in self.logical_indexes:
            if self.allowed_document_ids is None:
                raise ValueError("worker tenant scope requires allowed_document_ids (may be empty)")

    def to_audit_dict(self) -> dict:
        return {
            "principal_user_id": str(self.principal_user_id),
            "farm_id": str(self.farm_id) if self.farm_id else None,
            "farm_role": self.farm_role,
            "logical_indexes": sorted(self.logical_indexes),
            "doc_states": sorted(self.doc_states),
            "allowed_document_ids": (
                sorted(str(x) for x in self.allowed_document_ids)
                if self.allowed_document_ids is not None
                else None
            ),
            "snapshot_id": self.snapshot_id,
            "as_of": self.as_of.isoformat(),
            "top_k": self.top_k,
        }


def build_gov_scope(
    *,
    principal_user_id: UUID,
    snapshot_id: str | None,
    as_of: datetime,
    top_k: int = 8,
    tier_a_only: bool = True,
) -> RetrievalScope:
    indexes = frozenset({"gov_tier_a"}) if tier_a_only else frozenset({"gov_tier_a", "gov_tier_b"})
    return RetrievalScope(
        principal_user_id=principal_user_id,
        farm_id=None,
        farm_role="owner",
        logical_indexes=indexes,
        doc_states=frozenset({"active"}),
        allowed_document_ids=None,
        snapshot_id=snapshot_id,
        as_of=as_of,
        top_k=top_k,
    )


def build_tenant_scope(
    *,
    principal_user_id: UUID,
    farm_id: UUID,
    farm_role: Literal["owner", "worker"],
    allowed_document_ids: frozenset[UUID] | None,
    as_of: datetime,
    top_k: int = 8,
) -> RetrievalScope:
    if farm_role == "worker" and allowed_document_ids is None:
        raise ValueError("worker tenant scope requires allowed_document_ids")
    return RetrievalScope(
        principal_user_id=principal_user_id,
        farm_id=farm_id,
        farm_role=farm_role,
        logical_indexes=frozenset({TENANT_INDEX_KEY}),
        doc_states=frozenset({"active"}),
        allowed_document_ids=allowed_document_ids,
        snapshot_id=None,
        as_of=as_of,
        top_k=top_k,
    )
