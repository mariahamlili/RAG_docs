"""Parse CAI sprint tickets from docs/CAI_SPRINT_PLAN.md."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_MD = REPO_ROOT / "docs" / "CAI_SPRINT_PLAN.md"
TRACKER_JSON = REPO_ROOT / "docs" / "cai_sprint_tracker.json"

DONE_IDS = {f"CAI-{i:03d}" for i in range(1, 22)}
DEFERRED_IDS = {"CAI-081", "CAI-082"}
PARTIAL_IDS = {"CAI-009"}

ROW_PATTERN = re.compile(
    r"^\| \*\*(CAI-\d+)\*\* \| (.+?) \| ([^|]+) \| ([^|]+) \| (.+?) \|$"
)
WEEK_PATTERN = re.compile(r"^## Week (\d+)")
SECTION_PATTERN = re.compile(r"^### (.+)")


@dataclass
class Ticket:
    id: str
    week: str
    section: str
    title: str
    size: str
    depends: str
    description: str
    completion: str
    blockers: str


def load_tracker_overrides() -> dict[str, dict[str, str]]:
    if not TRACKER_JSON.exists():
        return {}
    data = json.loads(TRACKER_JSON.read_text(encoding="utf-8"))
    return data.get("tickets", {})


def default_completion(ticket_id: str) -> str:
    if ticket_id in DEFERRED_IDS:
        return "Deferred"
    if ticket_id in DONE_IDS:
        if ticket_id in PARTIAL_IDS:
            return "Done (partial)"
        return "Done"
    return "Not started"


def default_blockers(ticket_id: str, overrides: dict[str, dict[str, str]]) -> str:
    return overrides.get(ticket_id, {}).get("blockers", "")


def parse_tickets(plan_path: Path | None = None) -> list[Ticket]:
    plan_path = plan_path or PLAN_MD
    overrides = load_tracker_overrides()
    text = plan_path.read_text(encoding="utf-8")

    tickets: list[Ticket] = []
    current_week = ""
    current_section = "RAG core"

    for line in text.splitlines():
        week_match = WEEK_PATTERN.match(line)
        if week_match:
            current_week = f"Week {week_match.group(1)}"
            current_section = "RAG core"
            continue

        section_match = SECTION_PATTERN.match(line)
        if section_match:
            current_section = section_match.group(1).strip()
            continue

        row_match = ROW_PATTERN.match(line)
        if not row_match:
            continue

        ticket_id, title, size, depends, description = row_match.groups()
        override = overrides.get(ticket_id, {})
        completion = override.get("completion") or default_completion(ticket_id)
        blockers = override.get("blockers") or default_blockers(ticket_id, overrides)

        tickets.append(
            Ticket(
                id=ticket_id,
                week=current_week,
                section=current_section,
                title=title.strip(),
                size=size.strip(),
                depends=depends.strip(),
                description=description.strip(),
                completion=completion,
                blockers=blockers,
            )
        )

    return tickets


def summary_counts(tickets: list[Ticket]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ticket in tickets:
        counts[ticket.completion] = counts.get(ticket.completion, 0) + 1
    return counts
