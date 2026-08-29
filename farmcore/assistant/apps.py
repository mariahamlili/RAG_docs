from django.apps import AppConfig


class AssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assistant"

    def ready(self) -> None:
        # Import registries so entries register at startup.
        from assistant.registries import indexes, prompts, refusals, tools  # noqa: F401
