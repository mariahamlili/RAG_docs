import uuid

import pytest

from assistant.models import AuditEvent


@pytest.mark.django_db
def test_assistant_messages_stub_returns_refusal(api_client, owner_principal):
    user, farm = owner_principal
    api_client.force_login(user)
    session = api_client.session
    session["active_farm_id"] = str(farm.id)
    session.save()

    response = api_client.post(
        "/api/assistant/messages",
        {"message": "What is drought assistance?"},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "REFUSE"
    assert body["refusal_code"] == "OUT_OF_SCOPE"
    assert body["audit_id"]
    assert body["versions"]["schema_version"] == "chunks-v1"
    assert body["citations"] == []
    assert AuditEvent.objects.filter(audit_id=uuid.UUID(body["audit_id"])).exists()


@pytest.mark.django_db
def test_assistant_messages_requires_auth(api_client):
    response = api_client.post(
        "/api/assistant/messages",
        {"message": "hello"},
        format="json",
    )
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_assistant_messages_requires_active_farm(api_client, owner_principal):
    user, _farm = owner_principal
    api_client.force_login(user)
    response = api_client.post(
        "/api/assistant/messages",
        {"message": "hello"},
        format="json",
    )
    assert response.status_code == 403
    detail = response.json()
    if "code" in detail:
        assert detail["code"] == "no_active_farm"
    else:
        assert detail["detail"]["code"] == "no_active_farm"
