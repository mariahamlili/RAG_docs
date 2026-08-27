# DesignDoc → FarmCore Mapping

Traceability matrix from the general RAG design pattern (`DesignDoc.md`) through
FarmCore architecture, delivery phases, and priority classification. Use this
document to answer: *where did that DesignDoc requirement land, who owns it, and
when is it delivered?*

## Document Metadata

| Field | Value |
|---|---|
| Title | DesignDoc → FarmCore Mapping |
| Status | **Accepted** |
| Date | 2026-08-27 |
| Owning team | Assistant / Documents |
| Source pattern | `DesignDoc.md` — general multi-stage RAG |
| Target system | FarmCore POC — `assistant` and `documents` apps plus `RAG_docs` pipeline |
| Companion records | [`ARCHITECTURE.md`](ARCHITECTURE.md), [`PLAN.md`](PLAN.md), [`API.md`](API.md) |

## Priority Legend

| Priority | Meaning |
|---|---|
| **P0** | Required for POC demo; blocks phase exit |
| **P1** | Required for production-quality POC; delivered in plan but not first demo path |
| **P2** | Deferred with written trigger; not in POC scope until trigger fires |

## Ownership Legend

| Code | Team |
|---|---|
| **AI** | Assistant / Documents |
| **UI** | Frontend |
| **SCH** | Scheduling |
| **PL** | Project lead |

## Corpus Baseline (2026-08-27)

| Metric | Count |
|---|---|
| Tier A documents | 2,250 |
| Tier B documents | 1,054 |
| Tier C documents | 1,268 (excluded from all indexes) |
| Tier A PDFs fetched | 639 |
| Tier A PDFs text extracted | 605 |
| Tier A empty extractions | 34 |

---

## 1. Ingestion

| DesignDoc § | DesignDoc requirement | FarmCore decision | ARCHITECTURE / API anchor | Phase | Priority | Owner |
|---|---|---|---|---|---|---|
| 2.1 | Two separate indexes: gov corpus vs customer docs | One physical `document_chunks` table; logical separation via `farm_id` + `index_key`; never mixed in one retrieval call | §7.1, §5.1 | 3 (gov), 9 (tenant) | P0 | AI |
| 2.2 | Tier A default; B fallback; C excluded | Tier A = default index; Tier B = two-pass fallback only; Tier C not indexed | §4, §10 | 3 (A), 8 (B) | P0 / P1 | AI |
| 2.3 | Pre-chunking filters: empty, untitled, near-dup, boilerplate | Same filters with reason codes in `rejected.jsonl` | §6.1, §6.3 | 1 | P0 | AI |
| 2.4 | Structure-aware chunking 300–500 tok, 15% overlap, parent-child | Same; parent expansion at assembly | §6.3, §7.1 | 2 | P0 | AI |
| 2.4 | Tables as separate captioned chunks | pdfplumber/camelot extraction with caption | §6.3 | 2 | P0 | AI |
| 2.5 | Metadata schema with tenant_id, tier, source_url, content_hash | Full schema on `document_chunks` | §7.1 | 2 | P0 | AI |
| 2.6 | Customer doc ingestion: OCR, spreadsheets, photos, event-driven | Event-driven PDF/text only in POC; OCR/spreadsheet/photo deferred | §2.6 DesignDoc, §9 PLAN | 9 (PDF/text), 11+ (rest) | P0 / P2 | AI |
| 2.6 | Freshness/versioning: superseded_by, valid_from/to | Fields on schema; default retrieval prefers latest valid | §7.1 | 11+ | P2 | AI |
| 2.6 | Role-based access within tenant | Worker `allowed_document_ids`; owner full farm | §2.4, §7.2 | 9 | P0 | AI |
| 2.7 | Dense + sparse indexes; immutable content-addressed store | pgvector + Postgres FTS; `content_hash` for citation integrity | §3.2, §7.1 | 3 (dense), 4 (FTS) | P0 | AI |
| 2.7 | Qdrant or pgvector | pgvector accepted for POC | §3.2 | 3 | P0 | AI |
| 2.8 | JSONL chunk output; embedding null at chunk stage | Snapshot `chunks.jsonl` with null embeddings; embed on FarmCore import | §6.3 | 2–3 | P0 | AI |
| 2.8 | Validation gates: max 500 tok, source_url, parent_id | Hard-fail import validation | §6.4 | 2–3 | P0 | AI |
| — | **FarmCore-only:** Snapshot handoff artifact | Immutable `gov-a-<date>-<hash>` snapshot; checksums; atomic activation | §6 | 2–3 | P0 | AI |
| — | **FarmCore-only:** MinIO original bytes | `ObjectStorePort`; upload via `POST /api/documents` | API §4 | 9 | P0 | AI |
| — | **FarmCore-only:** Extraction candidates for structured data | `extraction_candidates` table; approve/reject API | API §4 | 9 | P0 | AI |
| — | **FarmCore-only:** Document archive (not delete) | `POST /api/documents/{id}/archive`; `doc_state = archived` | API §4.4 | 9 | P0 | AI |
| — | **FarmCore-only:** RQ background jobs for ingest | Async 202 pattern; idempotent jobs | API §1.7, §4.1 | 9 | P0 | AI |

---

## 2. Retrieval

| DesignDoc § | DesignDoc requirement | FarmCore decision | ARCHITECTURE / API anchor | Phase | Priority | Owner |
|---|---|---|---|---|---|---|
| 3 | Multi-stage pipeline: rewrite → recall → filter → rerank → MMR → pack | Fixed 9-stage pipeline; no agent loop in POC | §3.3, EXT §4 | 3–4 | P0 | AI |
| 3 | Stage 1: Query rewriting, HyDE | Understand stage: rewrite + optional HyDE for sparse | §3.3 stage 2 | 4 | P1 | AI |
| 3 | Stage 2: Hybrid dense + BM25, RRF | pgvector dense + Postgres FTS, RRF fusion | §3.2, §3.3 | 4 | P0 | AI |
| 3 | Stage 3: Metadata filtering | Scope predicates in SQL; doc_state, valid dates | §7.2 | 3 | P0 | AI |
| 3 | Stage 4: Cross-encoder rerank | `RerankPort`; top-50 → top-8 | §3.3 stage 7 | 4 | P0 | AI |
| 3 | Stage 5: MMR diversity | MMR after rerank | §3.3 stage 7 | 4 | P0 | AI |
| 3 | Stage 6: Context packing, token budget | Assembly stage with source-class floors | §3.3 stage 9 | 4 | P0 | AI |
| 3 | Query decomposition | Deferred | PLAN Phase 11+ | 11+ | P2 | AI |
| 3 | Self-querying metadata filters | Deferred | PLAN Phase 11+ | 11+ | P2 | AI |
| 3 | Agentic/iterative retrieval | Deferred; max 2–3 iterations if adopted | §5.2, PLAN 11+ | 11+ | P2 | AI |
| 3.1 | Tenant filter as hard query-level filter | `RetrievalScope` → SQL `WHERE`; no post-hoc Python filter | §2.4, §7.2 | 0 | P0 | AI |
| 3.1 | Tier A then A+B fallback before refuse | Two-pass fallback; single retry bound | §5.1 | 8 | P1 | AI |
| 3.1 | Blended queries: two separate retrieval calls | Tenant scope + gov scope; merge at assembly only | §5.1 | 10 | P0 | AI |
| — | **FarmCore-only:** `RetrievalScope` dataclass | Mandatory input; construction-time validation | §7.2 | 0 | P0 | AI |
| — | **FarmCore-only:** Named logical indexes | `gov_tier_a`, `gov_tier_b`, `tenant_doc` registry | §7.1, EXT §6 | 3 | P0 | AI |
| — | **FarmCore-only:** Corpus snapshot pinning | `snapshot_id` on gov rows; version tuple | §6, §11 | 3 | P0 | AI |
| — | **FarmCore-only:** Retrieval debug (feature flag) | Preview, traces, replay, chunk GET | API §6 | 10 | P1 | AI |
| — | **FarmCore-only:** Graceful degradation | Reranker/embedding/dense failures flagged | §12 | 4 | P0 | AI |
| — | **FarmCore-only:** Structured records NOT retrieved | Tasks, rules, schedules via tools only | §10 | 10 | P0 | AI |

---

## 3. Grounding, Citations, and Generation

| DesignDoc § | DesignDoc requirement | FarmCore decision | ARCHITECTURE / API anchor | Phase | Priority | Owner |
|---|---|---|---|---|---|---|
| 4 | Groundedness gate: confidence, coverage, conflict | Gate stage → `ANSWER` / `PARTIAL` / `REFUSE` | §3.3 stage 8 | 6 | P0 | AI |
| 4 | Refusal categories | Full refusal registry with actionable templates | §8, API §5.1 | 6 | P0 | AI |
| 4 | Hard rule: answer only from context | Registered prompt template; context-only constraint | §2.5 | 5 | P0 | AI |
| 4 | `TENANT_SCOPE_EMPTY` actionable refusal | Specific upload suggestion in template | §8 | 9 | P0 | AI |
| 5 | Claim-level citations with inline markers | `blocks` with markers; citation map in response | API §5.1 | 5 | P0 | AI |
| 5 | Entailment verification post-generation | `EntailmentPort`; drop/re-cite/downgrade failures | §3.3 stage 10 | 5 | P0 | AI |
| 5 | Clickable chunk text from immutable store | `content_hash` resolution; expandable citations | §2.5 | 5 | P0 | AI / UI |
| 5 | Source-type distinction in blended answers | `source_class` on citations; block labelling | §5.3, API §5.1 | 5 / 10 | P0 | AI / UI |
| 5 | Government URL prominently surfaced | `source_url` on gov citations | §2.5 | 5 | P0 | AI |
| — | **FarmCore-only:** facts vs guidance block types | `fact` \| `guidance` \| `warning` blocks | API §5.1 | 5 | P0 | AI |
| — | **FarmCore-only:** Structured outranks prose | Tool results verbatim; conflicts surfaced | §5.3 | 10 | P0 | AI |
| — | **FarmCore-only:** Tools before generation | No model tool loop in POC | §5.2 | 10 | P0 | AI |
| — | **FarmCore-only:** Draft lifecycle | `draft → confirmed/rejected/expired` | §2.7, API §5.1 | 10 | P0 | AI / SCH |
| — | **FarmCore-only:** Safety warnings | `SAFETY_VERIFY` warning code | §5.3 | 6 | P0 | AI |
| — | **FarmCore-only:** Answer contract in capabilities | `GET /api/capabilities` `answer_contract` | API §10 | 0 | P0 | AI |
| — | **FarmCore-only:** Weather never invented | Controlled weather tool; staleness flag | §4 knowledge sources | 10 | P0 | AI |

---

## 4. Audit and Evaluation

| DesignDoc § | DesignDoc requirement | FarmCore decision | ARCHITECTURE / API anchor | Phase | Priority | Owner |
|---|---|---|---|---|---|---|
| 6 | Structured immutable audit per request | Append-only audit; funnel + version tuple | §2.6, §11 | 0 | P0 | AI |
| 6 | Retrieval stages logged with IDs and scores | Per-stage audit buffer → persist | §3.3 | 4 | P0 | AI |
| 6 | Reproducibility / replay | `POST /api/retrieval/replay` with pinned snapshot | §11, API §6.4 | 10 | P1 | AI |
| 6 | Version-pin everything | `VersionTuple` resolved once in Admit | §11 | 0 / 3 | P0 | AI |
| 6 | Quality SLOs: refusal rate, entailment, citation failure | Evaluation harness metrics | PLAN Phase 7 | 7 | P0 | AI |
| 7 | Gold query set 100–300 | Regression suite in CI | PLAN Phase 7 | 7 | P0 | AI |
| 7 | Retrieval metrics: Recall@k, MRR, nDCG | Eval harness | PLAN Phase 7 | 7 | P0 | AI |
| 7 | Generation metrics: faithfulness, citation P/R | Eval harness | PLAN Phase 7 | 7 | P0 | AI |
| 7 | Refusal calibration curve | Threshold selection from eval | PLAN Phase 7 | 7 | P0 | AI |
| 7 | Regression on every config change | CI gate G12 | PLAN gates | 7 | P0 | AI |
| — | **FarmCore-only:** Audit as pipeline stage (fail request on write failure) | Stage 11; no degradation | §2.6, §12 | 0 | P0 | AI |
| — | **FarmCore-only:** Owner-only audit read/export | `GET /api/audit/events`, `POST /api/audit/exports` | API §9 | 10 | P0 | AI |
| — | **FarmCore-only:** Audit schema versioning | `schema_version: audit-v1` | EXT §7 | 0 | P0 | AI |
| — | **FarmCore-only:** User feedback on messages | `POST /api/assistant/messages/{id}/feedback` | API §5.3 | 10 | P1 | AI |
| — | **FarmCore-only:** `config_fingerprint` on responses | Short hash of version tuple | API §5.1 | 3 | P1 | AI |

---

## 5. FarmCore-Only Extras (No DesignDoc Source)

Requirements that exist in FarmCore architecture but are not explicit in
`DesignDoc.md`.

| Requirement | Rationale | Anchor | Phase | Priority | Owner |
|---|---|---|---|---|---|
| Session auth + CSRF; farm from session only | POC security model; no client-supplied farm_id | API §1 | 0 | P0 | AI |
| DRF error model with `code` + `request_id` | Supportable API errors | API §1.6 | 0 | P0 | AI |
| Async 202 job pattern | Upload, reindex, exports | API §1.7 | 0 / 9 | P0 | AI |
| Cursor pagination | List endpoints | API §1.9 | 0 | P0 | AI |
| Rate limits on assistant | Provider protection | API §1.10 | 0 | P0 | AI |
| Port/adapters (≤3 methods) | Swappable providers without framework | EXT §2 | 0 | P0 | AI |
| Four registries (tool, index, refusal, prompt) | Registries over conditionals | ARCH §2.3 | 0 | P0 | AI |
| `GET /api/capabilities` | Runtime introspection | API §10 | 0 | P0 | AI |
| `GET /healthz`, `GET /readyz` | Operational probes | API §2 | 0 | P0 | AI |
| Farm context dashboard snapshot | UI integration | API §3.3 | 0 | P0 | AI |
| Schedule explanations (read-only) | Explain FarmFlow without controlling it | API §8.1 | 10 | P1 | AI / SCH |
| Rule candidates from documents | Bridge docs → scheduling | API §8.2–8.5 | 9 / 10 | P1 | AI / SCH |
| Corpus admin API | Snapshot import, activate, rollback | API §7 | 3 | P0 | AI |
| Cross-farm leak CI tests | Tenant isolation enforcement | ARCH §13 | 0 / 9 | P0 | AI |
| Determinism test (FarmFlow) | Model never places tasks | ARCH §13, PLAN G9 | 0 | P0 | SCH / AI |
| OpenAPI from DRF serializers | Contracts-first | ARCH §2.1 | 0 | P0 | AI |
| Mandatory phase gates G1–G14 | Quality enforcement | PLAN gates | 0+ | P0 | AI / PL |
| Documentation standards + ADR process | Engineering discipline | DOCUMENTATION_STANDARDS.md | 0 | P0 | AI |
| Engineering diary | Decision/progress log | DOCUMENTATION_STANDARDS.md §6 | 0 | P1 | AI |

---

## 6. DesignDoc Items Explicitly Deferred (P2)

| DesignDoc § | Item | FarmCore disposition | Trigger (from PLAN) |
|---|---|---|---|
| 2.6 | OCR for scanned PDFs | Phase 11+ | Phase 1 review shows recoverable empty extractions, or tenant uploads predominantly scanned |
| 2.6 | Spreadsheet ingestion | Phase 11+ | Real onboarding data arrives as spreadsheets |
| 2.6 | Photo/image captioning | Phase 11+ | Demo requires image evidence with citeable captions |
| 2.6 | Document versioning UX | Phase 11+ | Re-upload causes stale answers |
| 2.7 | External BM25 (OpenSearch) | Phase 11+ | Postgres FTS underperforms on gold set |
| 2.7 | Qdrant migration | Phase 11+ | pgvector fails POC target; comparison favours Qdrant |
| 3 | Query decomposition | Phase 11+ | Multi-part coverage materially worse |
| 3 | Self-querying filters | Phase 11+ | Users express ignored metadata constraints |
| 3 | Agentic retrieval | Phase 11+ | Multi-hop failures fixable by bounded loop |
| 2.2 | Tier C cold index | Phase 11+ | Question provably answerable only from Tier C |
| 8 | LlamaIndex orchestration | Not adopted | Custom pipeline + registries instead |
| — | Cross-session chat history | Phase 11+ | Client scope change |
| — | Model-driven tool calling | Phase 11+ | Orchestrator mis-selects on gold set |
| — | DOCX ingestion | Phase 11+ | Onboarding data predominantly DOCX |

---

## 7. Phase → DesignDoc Coverage Summary

| Phase | DesignDoc sections primarily addressed | New FarmCore-only capabilities |
|---|---|---|
| 0 | 6 (audit shape), 3.1 (scope) | API contracts, ports, registries, health, capabilities |
| 1 | 2.2, 2.3 | Extraction quality report, rejected.jsonl |
| 2 | 2.4, 2.5, 2.8 | Snapshot artifact, parent-child hierarchy |
| 3 | 2.7, 3, 3.1 | Import command, dense retrieval, snapshot activation |
| 4 | 3 (stages 2–6) | Hybrid FTS, rerank, MMR, degradation |
| 5 | 5 | Citations, entailment, block types |
| 6 | 4 | Gate, refusal registry |
| 7 | 7 | Eval harness, calibrated thresholds |
| 8 | 2.2, 3.1 | Tier B fallback pass |
| 9 | 2.1, 2.6 | Tenant upload, candidates, archive, role eligibility |
| 10 | 3.1, 5, 6 | Tools, blended composition, audit export, replay |
| 11+ | Various P2 | OCR, agentic, Qdrant, etc. |

---

## 8. Scheduling Boundary Mapping

DesignDoc does not cover scheduling. FarmCore draws a hard boundary:

| Capability | DesignDoc analog | FarmCore owner | Priority |
|---|---|---|---|
| Document → rule candidates | — (FarmCore extension) | AI | P1 |
| Schedule explanations | — (FarmCore extension) | AI (explain) / SCH (state) | P1 |
| FarmFlow proposal generation | — | SCH | P0 |
| Task/rule write after approval | — | SCH | P0 |
| Assistant requests proposal | — | AI (draft tool) / SCH (execution) | P0 |
| Model in placement path | — | **Prohibited** | — |

---

## 9. Traceability Maintenance

When any of the following change, update this mapping in the same PR:

| Change type | Update |
|---|---|
| New DesignDoc section or revision | Add row to relevant §1–4 table |
| New FarmCore-only capability | Add row to §5 |
| Phase reorder or new phase | Update §7 and affected rows |
| Priority change | Update P0/P1/P2 column with ADR reference |
| Deferred item trigger fired | Move row from §6 to appropriate §1–4 table |

---

## 10. Related Records

- `DesignDoc.md` — source pattern
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — normative FarmCore architecture
- [`PLAN.md`](PLAN.md) — phased delivery
- [`API.md`](API.md) — HTTP contracts
- [`EXTENSIBILITY.md`](EXTENSIBILITY.md) — extension rules
