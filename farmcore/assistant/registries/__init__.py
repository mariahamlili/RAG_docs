"""Registry package — import submodules for side-effect registration."""

from assistant.registries import indexes, prompts, refusals, tools

__all__ = ["indexes", "prompts", "refusals", "tools"]
