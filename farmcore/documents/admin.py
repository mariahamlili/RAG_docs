from django.contrib import admin

from .models import CorpusSnapshot, DocumentChunk


@admin.register(CorpusSnapshot)
class CorpusSnapshotAdmin(admin.ModelAdmin):
    list_display = ("snapshot_id", "index_key", "is_active", "chunk_count", "activated_at")
    list_filter = ("is_active", "index_key")


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("chunk_id", "index_key", "doc_title", "snapshot_id", "doc_state")
    list_filter = ("index_key", "doc_state", "tier")
    search_fields = ("doc_title", "text")
