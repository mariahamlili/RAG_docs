# Documentation index

## CAI / Assistant track (normative)

These documents define the FarmCore assistant & knowledge system. When anything
else disagrees, **these win**.

| Document | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System shape, trust boundaries, corpus composition |
| [PLAN.md](PLAN.md) | Phases 0–10 delivery plan |
| [API.md](API.md) | `/api/` contracts and ownership |
| [EXTENSIBILITY.md](EXTENSIBILITY.md) | Ports, registries, extension rules |
| [MAPPING.md](MAPPING.md) | Design pattern → FarmCore traceability |
| [DOCUMENTATION_STANDARDS.md](DOCUMENTATION_STANDARDS.md) | How to write ADRs and diary entries |
| [CAI_SPRINT_PLAN.md](CAI_SPRINT_PLAN.md) | 4-week `CAI-###` ticket backlog |
| [OPENAPI_FREEZE.md](OPENAPI_FREEZE.md) | Phase 0 API freeze record |
| [adr/](adr/) | Architecture Decision Records 0001–0010 |
| [openapi/openapi.design.yaml](openapi/openapi.design.yaml) | Design-time OpenAPI v0.4.0 |

## Engineering diary

| Document | Purpose |
|---|---|
| [diary/Diary.md](diary/Diary.md) | Failures, decisions, measurements (append-only) |

## Reference & product notes

| Document | Purpose |
|---|---|
| [design/DesignDoc.md](design/DesignDoc.md) | General multi-stage RAG pattern (reference) |
| [product/](product/) | FarmCore product working notes & checklists |

When `product/` and `docs/*.md` disagree, **`docs/*.md` wins**.

## Code READMEs

| Folder | README |
|---|---|
| Corpus ingest | [`../ingest/README.md`](../ingest/README.md) |
| Django assistant | [`../farmcore/README.md`](../farmcore/README.md) |
| Shared schemas | [`../shared/schemas/document_chunks.md`](../shared/schemas/document_chunks.md) |
| Data on disk | [`../data/README.md`](../data/README.md) |
