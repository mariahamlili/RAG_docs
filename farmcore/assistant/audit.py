from __future__ import annotations

import uuid
from typing import Any

from django.db import transaction

from assistant.models import AuditEvent
from assistant.scope import RetrievalScope
from assistant.versions import VersionTuple


class AuditWriteError(Exception):
    pass


@transaction.atomic
def write_audit_event(
    *,
    audit_id: uuid.UUID,
    request_id: uuid.UUID,
    event_type: str,
    principal_user_id: uuid.UUID,
    farm_id: uuid.UUID | None,
    payload: dict[str, Any],
    conversation_id: uuid.UUID | None = None,
    message_id: uuid.UUID | None = None,
) -> AuditEvent:
    try:
        return AuditEvent.objects.create(
            audit_id=audit_id,
            request_id=request_id,
            event_type=event_type,
            principal_user_id=principal_user_id,
            farm_id=farm_id,
            conversation_id=conversation_id,
            message_id=message_id,
            payload=payload,
        )
    except Exception as exc:  # pragma: no cover - surfaced as 503
        raise AuditWriteError(str(exc)) from exc


def record_assistant_completion(
    *,
    audit_id: uuid.UUID,
    request_id: uuid.UUID,
    principal_user_id: uuid.UUID,
    farm_id: uuid.UUID,
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    scope: RetrievalScope,
    versions: VersionTuple,
    response_payload: dict[str, Any],
) -> AuditEvent:
    payload = {
        "scope": scope.to_audit_dict(),
        "versions": versions.to_dict(),
        "config_fingerprint": versions.fingerprint(),
        "response": response_payload,
    }
    return write_audit_event(
        audit_id=audit_id,
        request_id=request_id,
        event_type="assistant.message.completed",
        principal_user_id=principal_user_id,
        farm_id=farm_id,
        conversation_id=conversation_id,
        message_id=message_id,
        payload=payload,
    )
