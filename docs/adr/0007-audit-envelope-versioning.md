# ADR 0007: Audit envelope versioning — append-only typed metadata

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-27 |
| Deciders | Assistant / PL |
| Related | [`ARCHITECTURE.md`](../ARCHITECTURE.md) §2.6, §8, §11 |

## Context

The assistant pipeline has thirteen stages with degradation paths. Debugging a bad
answer requires knowing exactly which scope, corpus snapshot, models, and retrieval
funnel produced it — not reconstructed logs scattered across modules.

Audit cannot be best-effort logging: if the system cannot explain what it did, it
must not claim to have answered. Raw document bytes and secrets must never land in
audit storage.

## Decision

Treat **Audit as stage 13** with fail-closed persistence:

- Each prior stage appends **typed events** to an in-request buffer (`request.received`,
  `scope.resolved`, `retrieval.recall`, `gate.decision`, `verification.completed`, …).
- Stage 13 writes one **append-only envelope** per request: buffer + **`VersionTuple`**
  + serialised **`RetrievalScope`** + citation set with entailment scores + latencies.
- Envelope carries a **`schema_version`** (e.g. `audit-v1`); evolution adds versions,
  never mutates stored rows.
- Records are **append-only** for POC lifetime; owner-only search/export; no delete API.
- **Persist failure fails the request** — no degraded path.

Store concise structured metadata only; redact secrets; no raw MinIO bytes.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Append-only typed envelope + version tuple** | Replayable; bisect regressions; fail-closed | Storage growth; schema migration discipline |
| Unstructured application logs | Easy | Not queryable; incomplete funnel |
| Mutable audit rows | "Correction" UX | Destroys forensic value |
| Best-effort audit (warn on failure) | Higher availability | Violates explainability principle |

## Consequences

### Positive

- `audit_id` + `config_fingerprint` on every response; mandatory completeness test.
- Quality regressions bisect by diffing `VersionTuple` between audits.
- Replay re-executes retrieval against pinned snapshot and scope.

### Negative

- Higher write latency (~50 ms budget); DB pressure under load.
- Envelope schema changes require version bump and migration plan.

## Reversal criteria

Reopen if persist failure rate forces availability trade-off **and** PL accepts
weakened audit (strongly discouraged). Any softening requires new ADR.

## Verification

- [ ] Every `POST /api/assistant/messages` response includes `audit_id`.
- [ ] Persist failure returns 503; no answer body without audit row.
- [ ] Envelope contains full `VersionTuple` and executed scope JSON.
- [ ] Owner-only `/api/audit/events` returns filtered envelopes, not raw docs.
