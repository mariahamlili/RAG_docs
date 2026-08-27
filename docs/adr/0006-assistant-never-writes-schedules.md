# ADR 0006: Assistant never writes schedules

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-27 |
| Deciders | Assistant / Scheduling / PL |
| Related | [`ARCHITECTURE.md`](../ARCHITECTURE.md) §1.2, §2.7, §9 boundary 7 |

## Context

FarmFlow produces schedule proposals from **approved structured data** and
normalised weather. The same inputs must yield the same proposal — a reproducibility
requirement for owner trust and audit.

The assistant is probabilistic. Allowing it to place tasks, assign resources, or
commit slot ordering would introduce non-determinism into operational scheduling
and blur ownership between `assistant` and `scheduling` apps.

## Decision

The assistant **never writes schedules, task placements, or resource assignments**.

Permitted scheduling interactions:

- **Request** a proposal via the scheduling API (owner-initiated async job).
- **Explain** an existing schedule or unscheduled reason (`/api/assistant/schedule-explanations`).
- Emit **inert rule/task candidates** for owner review (`/api/assistant/rule-candidates`).

FarmFlow reads PostgreSQL structured rows only — never raw retrieval output or
model text. Trust boundary 7 is one-way: proposal *request* out; no placement in.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Assistant read/explain/candidate only** | Preserves determinism; clear ownership | Assistant cannot "just fix" the calendar |
| LLM-assisted placement inside FarmFlow | Flexible | Breaks reproducibility; prohibited |
| Assistant writes draft schedule rows | Faster demo | Draft/active confusion; same determinism risk |
| Full manual scheduling only | Simplest | Loses AI-assisted explanation value |

## Consequences

### Positive

- `Determinism` mandatory test applies only to FarmFlow with structured inputs.
- Scheduling team owns proposal algorithm changes without model regression risk.
- Assistant value stays in explanation and candidate extraction.

### Negative

- Users cannot ask the chat to "move Tuesday's spray" directly — they edit via
  scheduling UI or approve candidates first.

## Reversal criteria

Reopen only with explicit PL + Scheduling sign-off **and** a new determinism
strategy (e.g. human-confirmed placement suggestions with no auto-commit) documented
in a superseding ADR. Default: **do not reopen** for POC.

## Verification

- [ ] No assistant tool or orchestrator stage writes `schedules`, `jobs`, or placements.
- [ ] FarmFlow code path has zero imports from retrieval/generation modules.
- [ ] Mandatory determinism test: identical approved inputs → identical proposal.
- [ ] Schedule explanation endpoint reads structured state only.
