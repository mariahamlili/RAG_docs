from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from assistant.audit import AuditWriteError
from assistant.serializers import AssistantMessageRequestSerializer
from assistant.services.stub_orchestrator import handle_stub_message
from farms.auth import resolve_principal


class AssistantMessageView(APIView):
  """POST /api/assistant/messages — Phase 0 stub (CAI-010)."""

  def post(self, request: Request) -> Response:
    serializer = AssistantMessageRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    principal = resolve_principal(request)
    conversation_id = serializer.validated_data.get("conversation_id")

    try:
      payload = handle_stub_message(
        principal=principal,
        message=serializer.validated_data["message"],
        conversation_id=conversation_id,
      )
    except AuditWriteError:
      return Response(
        {"code": "audit_write_failed", "message": "Audit persistence failed."},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
      )

    return Response(payload, status=status.HTTP_200_OK)
