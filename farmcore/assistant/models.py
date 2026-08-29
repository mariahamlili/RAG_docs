import uuid

from django.db import models


class AuditEvent(models.Model):
    """Append-only audit envelope (audit-v1)."""

    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    audit_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    request_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    schema_version = models.CharField(max_length=16, default="audit-v1")
    farm_id = models.UUIDField(null=True, blank=True, db_index=True)
    principal_user_id = models.UUIDField(db_index=True)
    conversation_id = models.UUIDField(null=True, blank=True)
    message_id = models.UUIDField(null=True, blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["audit_id", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.audit_id}"
