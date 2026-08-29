import uuid

from django.db import models


class DocState(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class CorpusSnapshot(models.Model):
    """Exactly one row may be active at a time (enforced in application code)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    snapshot_id = models.CharField(max_length=64, unique=True)
    index_key = models.CharField(max_length=32, default="gov_tier_a")
    is_active = models.BooleanField(default=False)
    manifest_checksum = models.CharField(max_length=64)
    chunk_count = models.PositiveIntegerField(default=0)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"{self.snapshot_id} ({status})"


class DocumentChunk(models.Model):
    """
    Physical store for gov and tenant chunks (ARCHITECTURE §7.1).

    The `embedding` column is deferred to Phase 3 (CAI-031) once dimension is pinned.
  """

    chunk_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent_id = models.UUIDField(null=True, blank=True)
    document_id = models.UUIDField(null=True, blank=True)
    farm_id = models.UUIDField(null=True, blank=True, db_index=True)
    index_key = models.CharField(max_length=32, db_index=True)
    snapshot_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    tier = models.CharField(max_length=1, null=True, blank=True)
    doc_title = models.TextField()
    source_url = models.TextField(null=True, blank=True)
    heading_path = models.JSONField(default=list, blank=True)
    section_path = models.TextField(blank=True, default="")
    chunk_index = models.IntegerField()
    token_count = models.IntegerField()
    content_hash = models.CharField(max_length=64)
    text = models.TextField()
    doc_state = models.CharField(
        max_length=16,
        choices=DocState.choices,
        default=DocState.ACTIVE,
    )
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    superseded_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["farm_id", "index_key", "doc_state"]),
            models.Index(fields=["snapshot_id"]),
            models.Index(fields=["content_hash"]),
        ]
        ordering = ["snapshot_id", "chunk_index"]

    def __str__(self) -> str:
        return f"{self.index_key}:{self.chunk_id}"
