# Document Chunks Schema — Phase 0 Sign-off (CAI-003)

**Status:** Accepted for Phase 0 implementation  
**Date:** 2026-08-28  
**Companion:** [`ARCHITECTURE.md`](../docs/ARCHITECTURE.md) §7.1 · Django model `documents.DocumentChunk`

## Purpose

Single physical table for government and tenant chunks. Logical separation via
`farm_id` + `index_key`. Retrieval scope predicates are applied in SQL, never in
Python post-filters.

## Columns (implemented in `documents.DocumentChunk`)

| Column | Type | Gov | Tenant | Notes |
|---|---|---|---|---|
| `chunk_id` | UUID PK | ✓ | ✓ | |
| `parent_id` | UUID nullable | ✓ | ✓ | Parent expansion target |
| `document_id` | UUID nullable | null | ✓ | FK to tenant document |
| `farm_id` | UUID nullable | **NULL** | ✓ | NULL = public gov corpus |
| `index_key` | text | `gov_tier_a` / `gov_tier_b` | `tenant_doc` | Never mixed in one retrieval call |
| `snapshot_id` | text nullable | ✓ | null | Content-addressed gov snapshot |
| `tier` | text nullable | A/B | null | |
| `doc_title` | text | ✓ | ✓ | |
| `source_url` | text nullable | live URL | null | |
| `heading_path` | text[] | ✓ | ✓ | JSON in Django |
| `section_path` | text | ✓ | ✓ | |
| `chunk_index` | int | ✓ | ✓ | |
| `token_count` | int | ✓ | ✓ | max 500 at import |
| `content_hash` | text | ✓ | ✓ | sha256 hex |
| `text` | text | ✓ | ✓ | |
| `doc_state` | text | active/archived | active/archived | |
| `valid_from` | timestamptz | optional | optional | Phase 11+ UX |
| `valid_to` | timestamptz | optional | optional | |
| `superseded_by` | UUID | optional | optional | |
| `created_at` | timestamptz | ✓ | ✓ | |

## Deferred to Phase 3 (CAI-031)

| Column | Reason |
|---|---|
| `embedding vector(dim)` | Dimension unknown until embedding model pinned |
| `text_search tsvector` | Phase 4 FTS migration |

## Index plan (apply with migrations in Phases 3–4)

- HNSW partial on `embedding` where `farm_id IS NULL AND doc_state = 'active'`
- HNSW partial on `embedding` where `farm_id IS NOT NULL AND doc_state = 'active'`
- GIN on `text_search` (gov / tenant partials)
- B-tree on `(farm_id, index_key, doc_state)`
- B-tree on `snapshot_id`, `content_hash`

## Sign-off checklist

- [x] Schema documented and Django model merged
- [ ] UI team acknowledged (track in OPENAPI_FREEZE.md)
- [ ] Scheduling team acknowledged data boundaries (no chunk writes from SCH)
