# ADR 0001: pgvector for v1 with VectorStore port

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-27 |
| Deciders | Assistant / Documents / PL |
| Related | [`ARCHITECTURE.md`](../ARCHITECTURE.md) §7, §12 |

## Context

FarmCore needs dense semantic recall over government and tenant document chunks.
The POC runs on a single PostgreSQL instance (with PostGIS) inside Docker Compose.
Operational data and embeddings must stay transactionally consistent — archiving a
document must remove it from retrieval atomically with its row state.

A separate vector database adds sync complexity, another failure domain, and
breaks single-transaction scope predicates. The embedding dimension is not fixed
until Phase 3, but the storage choice must be settled in Phase 0.

## Decision

Use **PostgreSQL with the `pgvector` extension** as the v1 dense store. All
similarity search goes through a **`VectorStore` port** owned by `documents`, with
one POC adapter (`PgVectorStore`) that executes parameterised queries carrying the
full `RetrievalScope` predicate.

Call sites never import pgvector types or raw SQL. Qdrant or another engine may
replace the adapter only after a documented comparison ADR.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **pgvector + `VectorStore` port** | One DB, atomic scope+state, Compose-simple, partial HNSW indexes | Weaker at very large scale; tuning less mature than dedicated engines |
| Qdrant (or similar) from day one | Purpose-built ANN, horizontal scaling story | Cross-store consistency; scope filter duplication; extra ops |
| Embeddings in application memory | Zero infra | Not durable; no farm isolation; unusable for POC |

## Consequences

### Positive

- Retrieval, lexical FTS, and document lifecycle share one schema and backup.
- Partial HNSW indexes on `farm_id IS NULL` / `IS NOT NULL` give isolation without
  separate stores.
- Adapter swap is bounded — only `PgVectorStore` changes if migration is ever approved.

### Negative

- Embedding column migration is blocked until dimension is pinned (Phase 3).
- Recall/latency SLOs must be measured; failure triggers a gated re-evaluation.

## Reversal criteria

Reopen if, on the gold evaluation set, pgvector recall or p95 latency fails the
POC target **and** a written comparison on retrieval quality, filtering, ops,
cost, and deployment fit favours an alternative. Requires new ADR + checklist update.

## Verification

- [ ] `VectorStore` port declared with typed inputs/outputs; no provider types leak.
- [ ] `PgVectorStore` applies every `RetrievalScope` field as a SQL predicate.
- [ ] Cross-farm leak test passes on all retrieval entry points.
- [ ] Degradation to FTS-only on vector query error is audited (`retrieval.degraded`).
