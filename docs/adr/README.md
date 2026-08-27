# Architecture Decision Records

Normative decisions extracted from [`ARCHITECTURE.md`](../ARCHITECTURE.md). Each ADR
is small, reversible only through a new ADR, and linked from the architecture
change process.

| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-pgvector-for-v1.md) | pgvector for v1 with `VectorStore` port | Accepted | 2026-08-27 |
| [0002](0002-postgres-fts-for-sparse.md) | PostgreSQL FTS for sparse recall (not OpenSearch) | Accepted | 2026-08-27 |
| [0003](0003-logical-indexes-one-table.md) | Logical indexes on one table + `RetrievalScope` | Accepted | 2026-08-27 |
| [0004](0004-openapi-design-then-generated-ci-diff.md) | OpenAPI design-then-generated with CI diff | Accepted | 2026-08-27 |
| [0005](0005-claim-level-citations-entailment.md) | Claim-level citations with LLM-as-judge entailment | Accepted | 2026-08-27 |
| [0006](0006-assistant-never-writes-schedules.md) | Assistant never writes schedules | Accepted | 2026-08-27 |
| [0007](0007-audit-envelope-versioning.md) | Audit envelope versioning — append-only typed metadata | Accepted | 2026-08-27 |
| [0008](0008-tier-b-fallback-tier-c-excluded.md) | Tier B fallback; Tier C excluded | Accepted | 2026-08-27 |
| [0009](0009-immutable-corpus-snapshots.md) | Immutable corpus snapshots | Accepted | 2026-08-27 |
| [0010](0010-registries-not-frameworks.md) | Registries, not frameworks | Accepted | 2026-08-27 |

## Process

1. Copy [`0000-template.md`](0000-template.md) to the next number.
2. Set status to **Proposed**; discuss in PR.
3. On acceptance, set status and date; update this index and `ARCHITECTURE.md` if
   the decision is material.
4. Supersede by adding a new ADR — do not rewrite history.
