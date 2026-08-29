from __future__ import annotations

from dataclasses import dataclass

REGISTRY_VERSION = "prompts-v0"


@dataclass(frozen=True)
class PromptEntry:
    prompt_id: str
    version: str
    description: str
    system_template: str


_REGISTRY: dict[str, PromptEntry] = {
    "refusal-stub-v0": PromptEntry(
        prompt_id="refusal-stub-v0",
        version="0.1.0",
        description="Phase 0 hardcoded refusal stub",
        system_template="You are a farm assistant. Refuse out-of-scope requests.",
    ),
    "answer-gov-v0": PromptEntry(
        prompt_id="answer-gov-v0",
        version="0.1.0",
        description="Gov-corpus answer template (Phase 3+)",
        system_template="Answer using only the provided context with citation markers.",
    ),
}


def get_prompt(prompt_id: str) -> PromptEntry:
    return _REGISTRY[prompt_id]


def all_prompts() -> dict[str, PromptEntry]:
    return dict(_REGISTRY)


def registry_version() -> str:
    return REGISTRY_VERSION
