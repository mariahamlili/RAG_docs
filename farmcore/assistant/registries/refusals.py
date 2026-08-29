from __future__ import annotations

from dataclasses import dataclass

REGISTRY_VERSION = "refusals-v0"


@dataclass(frozen=True)
class RefusalEntry:
    code: str
    user_message: str
    action_hint: str | None = None


_REGISTRY: dict[str, RefusalEntry] = {
    "NO_RELEVANT_CONTEXT": RefusalEntry(
        code="NO_RELEVANT_CONTEXT",
        user_message="I could not find relevant information in the indexed corpus for that question.",
        action_hint="Try rephrasing or narrowing your question.",
    ),
    "INSUFFICIENT_COVERAGE": RefusalEntry(
        code="INSUFFICIENT_COVERAGE",
        user_message="I can only answer part of your question with the available sources.",
        action_hint="Ask about the uncovered part separately.",
    ),
    "CONFLICTING_SOURCES": RefusalEntry(
        code="CONFLICTING_SOURCES",
        user_message="The sources I found disagree materially; I cannot pick one answer silently.",
        action_hint="Review the cited documents or ask for clarification.",
    ),
    "OUT_OF_SCOPE": RefusalEntry(
        code="OUT_OF_SCOPE",
        user_message="That question is outside agriculture and farm operations assistance for this assistant.",
        action_hint="Ask about crops, livestock, biosecurity, drought support, or your farm records.",
    ),
    "ACCESS_DENIED": RefusalEntry(
        code="ACCESS_DENIED",
        user_message="You do not have permission to access the information needed to answer that.",
        action_hint="Contact your farm owner if you need access.",
    ),
    "TENANT_SCOPE_EMPTY": RefusalEntry(
        code="TENANT_SCOPE_EMPTY",
        user_message="I do not have the farm documents needed to answer that question.",
        action_hint="Upload the relevant document (for example a soil test PDF).",
    ),
    "PROVIDER_UNAVAILABLE": RefusalEntry(
        code="PROVIDER_UNAVAILABLE",
        user_message="The assistant is temporarily unavailable. Please try again shortly.",
        action_hint="Retry in a few minutes.",
    ),
}


def get_refusal(code: str) -> RefusalEntry:
    return _REGISTRY[code]


def all_refusals() -> dict[str, RefusalEntry]:
    return dict(_REGISTRY)


def registry_version() -> str:
    return REGISTRY_VERSION
