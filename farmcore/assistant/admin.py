from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "audit_id", "farm_id", "created_at")
    list_filter = ("event_type",)
    search_fields = ("audit_id", "request_id")
