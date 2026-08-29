# Shared contracts

Cross-track schemas used by **both** `ingest/` (snapshot build) and `farmcore/` (import).

| Artifact | Purpose |
|---|---|
| [`schemas/chunks-v1.schema.json`](schemas/chunks-v1.schema.json) | Chunk record JSON Schema |
| [`schemas/chunks_validator.py`](schemas/chunks_validator.py) | Standalone validator (CAI-007) |
| [`schemas/document_chunks.md`](schemas/document_chunks.md) | `document_chunks` table sign-off (CAI-003) |

FarmCore settings point at `shared/schemas/` via `CHUNKS_SCHEMA_PATH`.
