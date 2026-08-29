from __future__ import annotations

import uuid

from rest_framework import serializers


class AssistantMessageRequestSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(min_length=1, max_length=4000)

    def validate_message(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Message must not be empty.")
        return cleaned
