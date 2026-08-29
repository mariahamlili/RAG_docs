from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

REGISTRY_VERSION = "tools-v0"


@dataclass(frozen=True)
class ToolEntry:
    tool_name: str
    version: str
    handler: Callable[..., dict]
    tool_class: Literal["read", "draft"]
    required_role: Literal["owner", "worker"]
    description: str


_REGISTRY: dict[str, ToolEntry] = {}


def register_tool(entry: ToolEntry) -> None:
    _REGISTRY[entry.tool_name] = entry


def get_tool(name: str) -> ToolEntry:
    return _REGISTRY[name]


def all_tools() -> dict[str, ToolEntry]:
    return dict(_REGISTRY)


def registry_version() -> str:
    return REGISTRY_VERSION
