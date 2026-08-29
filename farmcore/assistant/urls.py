from django.urls import path

from assistant.views import AssistantMessageView

urlpatterns = [
    path("assistant/messages", AssistantMessageView.as_view(), name="assistant-messages"),
]
