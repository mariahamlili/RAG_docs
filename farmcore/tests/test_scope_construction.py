from datetime import datetime, timezone
from uuid import uuid4

import pytest

from assistant.scope import (
    RetrievalScope,
    build_gov_scope,
    build_tenant_scope,
)


def test_gov_scope_constructs():
    scope = build_gov_scope(
        principal_user_id=uuid4(),
        snapshot_id="gov-a-20260828-abc",
        as_of=datetime.now(timezone.utc),
    )
    assert scope.farm_id is None
    assert scope.logical_indexes == frozenset({"gov_tier_a"})


def test_tenant_and_gov_indexes_cannot_mix():
    with pytest.raises(ValueError, match="cannot be mixed"):
        RetrievalScope(
            principal_user_id=uuid4(),
            farm_id=uuid4(),
            farm_role="owner",
            logical_indexes=frozenset({"tenant_doc", "gov_tier_a"}),
            doc_states=frozenset({"active"}),
            allowed_document_ids=None,
            snapshot_id=None,
            as_of=datetime.now(timezone.utc),
            top_k=8,
        )


def test_worker_tenant_scope_requires_allowed_document_ids():
    with pytest.raises(ValueError, match="allowed_document_ids"):
        build_tenant_scope(
            principal_user_id=uuid4(),
            farm_id=uuid4(),
            farm_role="worker",
            allowed_document_ids=None,
            as_of=datetime.now(timezone.utc),
        )


def test_worker_tenant_scope_allows_empty_allowed_set():
    scope = build_tenant_scope(
        principal_user_id=uuid4(),
        farm_id=uuid4(),
        farm_role="worker",
        allowed_document_ids=frozenset(),
        as_of=datetime.now(timezone.utc),
    )
    assert scope.allowed_document_ids == frozenset()
