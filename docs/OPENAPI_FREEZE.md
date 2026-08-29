# OpenAPI / API Contract Freeze — Phase 0 (CAI-009)

**Status:** Frozen for Phase 0 stub implementation  
**Date:** 2026-08-28  
**Design artifact:** [`docs/openapi/openapi.design.yaml`](../docs/openapi/openapi.design.yaml) v0.4.0  
**Normative prose:** [`docs/API.md`](../docs/API.md)

## Scope frozen in Phase 0

| Group | Endpoints | Notes |
|---|---|---|
| Assistant | `POST /api/assistant/messages` | Stub refusal response; schema-complete payload |
| Error envelope | All `/api/*` | `code`, `message`, `request_id` |
| Audit | Event shape `audit-v1` | Written on every assistant message |

## Review sign-off (fill when reviewed)

| Team | Reviewer | Date | Status |
|---|---|---|---|
| UI | _pending_ | — | Not started |
| Scheduling | _pending_ | — | Not started |
| Assistant / Documents | CAI-010 implementer | 2026-08-28 | Stub merged |

## Breaking change policy (Phase 0 → 1)

- Additive response fields allowed without version bump.
- Renaming/removing response fields requires OpenAPI minor bump + UI notice.
- `POST /api/assistant/messages` request shape is frozen (`conversation_id`, `message` only).
- Active farm and `FarmRole` remain session-derived — never request fields.

## Generator note

FarmCore ships a hand-written DRF view for Phase 0. OpenAPI remains design-time until
CI diff gate lands (ADR-0004, Phase 0+).
