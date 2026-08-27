# ADR 0002: PostgreSQL FTS for sparse recall (not OpenSearch)

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-27 |
| Deciders | Assistant / Documents |
| Related | [`ARCHITECTURE.md`](../ARCHITECTURE.md) §7.1, §8 step 6 |

## Context

Hybrid retrieval fuses dense (pgvector) and sparse (lexical) recall before RRF and
cross-encoder reranking. Government corpus queries include exact terms — chemical
names, regulation numbers, place names — where semantic similarity alone misses.

The POC must not add a second search cluster. Compose already runs PostgreSQL; the
chunk table will carry generated `tsvector` columns with GIN indexes partitioned by
gov vs tenant partial predicates.

## Decision

Use **PostgreSQL full-text search (`tsvector` + GIN)** as the sole sparse recall
mechanism for v1. **Do not deploy OpenSearch, Elasticsearch, or an external BM25
service** in the POC.

Sparse and dense queries share the same `document_chunks` table and the same
`RetrievalScope` WHERE clauses. RRF merges candidate lists in application code.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **Postgres FTS** | No new service; same transaction boundary as dense; partial GIN indexes | Weaker tuning than dedicated BM25; English-centric defaults |
| OpenSearch / Elasticsearch | Mature BM25, analyzers, scale | Second cluster, sync lag, duplicated scope enforcement |
| Dense-only (skip sparse) | Simplest pipeline | Misses exact-term recall on gold set; known failure mode |

## Consequences

### Positive

- One query plan path for scope + lexical filter; no post-hoc Python filtering.
- Embedding outage degrades to FTS-only with a declared audit flag.
- Ops surface stays PostgreSQL-only for retrieval.

### Negative

- Analyzer choice and stemming affect recall; must be pinned in `VersionTuple`.
- If gold-set exact-term recall fails SLO, external BM25 becomes a gated revisit.

## Reversal criteria

Reopen if Postgres FTS demonstrably underperforms on exact-term recall in the
mandatory gold evaluation set **and** operational cost of an external sparse index
is acceptable for POC demo timelines.

## Verification

- [ ] `text_search` generated column and gov/tenant partial GIN indexes migrated.
- [ ] Hybrid recall test: known exact-term query returns target chunk via FTS path.
- [ ] FTS-only degradation path tested when dense recall is disabled.
- [ ] No OpenSearch/Elasticsearch service in Compose or deployment manifests.
