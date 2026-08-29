from __future__ import annotations

import uuid
from datetime import datetime, timezone

from django.conf import settings
from django.utils import timezone as dj_timezone

from accounts.user_uuid import user_uuid
from assistant.audit import AuditWriteError, record_assistant_completion
from assistant.registries.refusals import get_refusal
from assistant.scope import build_gov_scope
from assistant.versions import version_tuple_from_settings
from farms.auth import Principal


def _utc_now() -> datetime:
    return dj_timezone.now()


def handle_stub_message(*, principal: Principal, message: str, conversation_id: uuid.UUID | None) -> dict:
    """
    Phase 0 stub orchestrator: Admit → build scope → hardcoded REFUSE/OUT_OF_SCOPE.

    No retrieval, generation, or tools in this phase.
    """
    request_id = uuid.uuid4()
    audit_id = uuid.uuid4()
    message_id = uuid.uuid4()
    conversation_id = conversation_id or uuid.uuid4()

    active_snapshot = None  # Phase 3 resolves from corpus_snapshots
    scope = build_gov_scope(
        principal_user_id=user_uuid(principal.user),
        snapshot_id=active_snapshot,
        as_of=_utc_now(),
    )

    versions = version_tuple_from_settings(settings.CAI_STUB_VERSIONS)
    refusal = get_refusal("OUT_OF_SCOPE")

    response = {
        "conversation_id": str(conversation_id),
        "message_id": str(message_id),
        "audit_id": str(audit_id),
        "request_id": str(request_id),
        "decision": "REFUSE",
        "refusal_code": refusal.code,
        "refusal_detail": refusal.user_message,
        "answer_text": None,
        "blocks": [],
        "citations": [],
        "general_guidance": [],
        "warnings": [],
        "refusals": [
            {
                "code": refusal.code,
                "message": refusal.user_message,
                "action_hint": refusal.action_hint,
            }
        ],
        "drafts": [],
        "tools_used": [],
        "retrieval": {
            "scopes_executed": [
                {
                    "scope_type": "gov_tier_a",
                    "index_keys": sorted(scope.logical_indexes),
                    "snapshot_id": scope.snapshot_id,
                    "stages": [],
                    "final_chunk_ids": [],
                }
            ],
            "fallback_invoked": False,
            "degraded": [],
        },
        "versions": versions.to_dict(),
        "config_fingerprint": versions.fingerprint(),
        "retrieved_at": _utc_now().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "latency_ms": {
            "total": 5,
            "admit": 2,
            "understand": 0,
            "plan": 0,
            "tools": 0,
            "retrieve": 0,
            "rank": 0,
            "assemble": 0,
            "gate": 1,
            "generate": 0,
            "verify": 0,
            "audit": 2,
        },
        "stub": True,
        "input_message_preview": message[:120],
    }

    try:
        record_assistant_completion(
            audit_id=audit_id,
            request_id=request_id,
            principal_user_id=user_uuid(principal.user),
            farm_id=principal.farm.id,
            conversation_id=conversation_id,
            message_id=message_id,
            scope=scope,
            versions=versions,
            response_payload=response,
        )
    except AuditWriteError as exc:
        raise AuditWriteError(str(exc)) from exc

    return response
