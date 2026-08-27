# ADR 0003: Logical indexes on one table + RetrievalScope

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-27 |
| Deciders | Assistant / Documents |
| Related | [`ARCHITECTURE.md`](../ARCHITECTURE.md) §7 |

## Context

Retrievable text spans three source classes: gov Tier A, gov Tier B (fallback),
and tenant uploads. Each class has different ownership, activation, and scope
rules. Separate physical tables or vector stores would complicate archival,
supersession, and transactional consistency with document state.

Every retrieval bug class traced so far involves missing scope predicates — not
table count. The architecture requires that **no function accepts a bare query
string**.

## Decision

Store all chunks in one physical **`document_chunks`** table. Separate corpora
with an **`index_key`** discriminator (`gov_tier_a`, `gov_tier_b`, `tenant_doc`).

Every retrieval call takes a frozen **`RetrievalScope`** built **only in Admit**:
principal, farm, role, `logical_indexes`, doc states, optional document allow-list,
pinned `snapshot_id`, `as_of`, and `top_k`. Each field becomes a SQL predicate in
the same query as similarity/FTS search.

**`tenant_doc` must not mix with `gov_*` in one scope** — blended queries issue
two scoped calls.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **One table + `RetrievalScope`** | Atomic archive; one migration; partial indexes; audit replay | Wide table; index_key discipline required |
| Separate table per index | Obvious isolation | Cross-table consistency; duplicated schema |
| Separate vector DB per tier | Independent scaling | Scope enforcement in app layer; sync risk |

## Consequences

### Positive

- Archiving sets `doc_state = 'archived'` and immediately excludes from all indexes.
- Partial HNSW/GIN indexes match gov vs tenant without duplicate embeddings.
- Serialised scope in audit enables exact replay.

### Negative

- Construction-time validation must reject illegal index combinations.
- Static CI check required: no Python-side post-filter by `farm_id`.

## Reversal criteria

Reopen only if measured query plans show unacceptable cross-index interference at
POC corpus size **or** a regulated compliance requirement mandates physical
separation of tenant bytes from gov bytes (not current POC scope).

## Verification

- [ ] `RetrievalScope` dataclass with construction-time validation merged.
- [ ] Mixing `tenant_doc` + `gov_tier_a` in one scope raises at construction.
- [ ] Mandatory tests: cross-farm leak, scope construction, no post-hoc filtering.
- [ ] Index registry documents every `index_key` with tier and default eligibility.
