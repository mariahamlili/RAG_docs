# FarmCore AI/RAG Delivery Plan

Phased delivery plan for the FarmCore assistant and document-retrieval track. Each
phase has entry criteria, concrete deliverables, testable exit criteria, named
risks, and a single accountable owner. Phases are ordered by quality impact per
unit of effort, not by architectural tidiness.

## Document Metadata

| Field | Value |
|---|---|
| Title | FarmCore AI/RAG Delivery Plan |
| Status | **Accepted** |
| Date | 2026-08-27 |
| Owning team | Assistant / Documents |
| Companion record | [`ARCHITECTURE.md`](ARCHITECTURE.md) — normative architecture |
| Applies to | FarmCore POC, `assistant` and `documents` Django apps, plus the `RAG_docs` corpus pipeline |
| Planning horizon | POC delivery; Phase 11+ is explicitly deferred |
| Change process | Phase reordering requires project-lead sign-off; adding a deliverable inside a phase does not |
| Review cadence | At each phase gate |

## Ownership Legend

| Code | Team | Accountable for |
|---|---|---|
| **AI** | Assistant / Documents | Corpus pipeline, ingestion, retrieval, orchestrator, tools, citations, gate, audit, evaluation |
| **UI** | Frontend | Django templates, HTMX fragments, static assets, citation rendering, map rendering, review surfaces |
| **SCH** | Scheduling | Rules, templates, tasks, schedules, FarmFlow determinism, weather constraint evaluation |
| **PL** | Project lead | Cross-team sequencing, schema and migration arbitration, environments, demo script, provider budget sign-off |

One owner per row is accountable. Additional codes in a row are required
collaborators, not co-owners.

## Corpus Baseline

Every phase below assumes these measured figures.

| Metric | Count | Consequence for the plan |
|---|---|---|
| Tier A documents | 2,250 | The default index; all of Phases 1–7 target Tier A only |
| Tier B documents | 1,054 | Fallback pool, enters in Phase 8 |
| Tier C documents | 1,268 | Never indexed; no phase touches it |
| Tier A source PDFs fetched | 639 | The extraction working set |
| Tier A PDFs extracted successfully | 605 | 94.7% extraction rate |
| Tier A PDFs with empty extraction | 34 | Reviewed in Phase 1; OCR recovery deferred to Phase 11+ |

---

## Phase 0 — Foundations and Contracts

**Owner: AI** · Collaborators: PL, UI, SCH

Nothing is built until the shapes are agreed. This phase produces contracts and a
running skeleton, not features.

| | |
|---|---|
| **Entry criteria** | Architecture accepted. Django apps (`accounts`, `farms`, `documents`, `assistant`, `scheduling`) exist. Docker Compose stack (Django, PostgreSQL with pgvector and PostGIS, Redis, RQ worker and scheduler, MinIO) starts clean on every developer machine. |

**Deliverables**

1. `document_chunks` schema agreed on paper, including `index_key`, `farm_id`
   nullability, `snapshot_id`, `doc_state`, and the supersession fields. The
   `embedding` column is specified but not migrated — dimension is unknown until
   Phase 3.
2. `RetrievalScope` dataclass defined with construction-time validation, plus the
   rule that mixing `tenant_doc` with a `gov_*` index raises.
3. Port interfaces declared with typed signatures and no-op or fixture adapters:
   `EmbeddingPort`, `GenerationPort`, `RerankPort`, `EntailmentPort`,
   `ExtractionPort`, `ObjectStorePort`.
4. The four registries scaffolded (tool, index, refusal, prompt), each with a
   version constant and a completeness test.
5. Chunk record schema `chunks-v1` with a standalone validator usable by both
   `RAG_docs` and FarmCore.
6. Audit event schema and the `VersionTuple`, with an append-only audit table
   migration.
7. `POST /api/assistant/messages` stubbed end to end: real auth, real farm scoping,
   real audit record, hardcoded refusal response.
8. CI running the mandatory-test skeletons from `ARCHITECTURE.md` §13, initially
   as expected-failure placeholders where implementation is absent.

| | |
|---|---|
| **Exit criteria** | A request to `POST /api/assistant/messages` authenticates, resolves the active farm, verifies `FarmRole`, constructs a `RetrievalScope`, returns a schema-valid refusal, and writes a complete audit record including the version tuple. Cross-farm leak and scope-construction tests pass against the stub. UI can generate a client from the OpenAPI schema. |
| **Risks** | *Contract churn* — mitigated by keeping the stub response schema-complete so later phases fill values rather than reshape the payload. *Premature abstraction* — mitigated by the one-port-one-adapter rule; no generic plug-in framework. *Embedding dimension unknown* — accepted, deliberately deferred to Phase 3. |

---

## Phase 1 — Corpus Extraction and Filtering

**Owner: AI**

Turn 639 fetched Tier A PDFs into clean, reviewed text. This is the phase where
corpus quality is actually decided.

| | |
|---|---|
| **Entry criteria** | Phase 0 exit met. Tier A manifest present with 639 rows. Extraction tooling pinned in `requirements.txt`. |

**Deliverables**

1. Text extraction across all 639 Tier A PDFs, reproducing the measured baseline:
   605 successful, 34 empty.
2. Pre-chunking filters applied to extracted text, each writing a reason code to
   `rejected.jsonl`:
   - `EMPTY_EXTRACTION` — under 50 tokens.
   - `LIKELY_NON_TEXT_ASSET` — "Untitled document" title with under 100 tokens.
   - `NEAR_DUPLICATE` — normalised-text similarity above 0.9, retaining one and
     recording a pointer to the kept `doc_id`.
   - `TIER_EXCLUDED` — anything not Tier A.
3. Boilerplate stripping: short lines appearing on more than half a document's
   pages, plus a blocklist of navigation and accessibility phrases.
4. **Manual review of all 34 empty extractions**, classified as recoverable-with-
   OCR versus genuinely non-textual. The recoverable list becomes the Phase 11+
   OCR trigger evidence.
5. **Manual review of a 30-document near-duplicate sample**, confirming that
   different years of the same report title are not being collapsed.
6. Extraction quality report: token distribution, per-topic document counts,
   rejection counts by reason.

| | |
|---|---|
| **Exit criteria** | 605 documents carry clean extracted text. Every one of the 639 documents is either extracted or in `rejected.jsonl` with a reason — no silent drops. Both manual reviews are written up. The pipeline is idempotent: a rerun produces byte-identical output. |
| **Risks** | *Over-aggressive near-duplicate collapse* removes genuinely distinct annual reports — mitigated by the mandatory sample review and by logging rather than deleting. *Boilerplate stripping removes real content* in short documents — mitigated by applying it only above a page-count threshold and diffing a sample. *Silent extraction degradation* on a tooling upgrade — mitigated by asserting the 605/34 split in CI. |

---

## Phase 2 — Chunking and Snapshot Build

**Owner: AI**

| | |
|---|---|
| **Entry criteria** | Phase 1 exit met. `chunks-v1` schema and validator available from Phase 0. |

**Deliverables**

1. Structure-aware chunker, in strict priority order: split on headings; accumulate
   paragraphs into 300–500 token chunks with roughly 15% overlap within a section;
   never split a table mid-row; never cross a heading boundary; fall back to
   sentence boundaries only when a single paragraph exceeds 500 tokens.
2. Parent-child hierarchy: children are embedded and matched, parents are passed to
   generation. Every child carries a resolvable `parent_id`.
3. Table extraction as separate chunks with an auto-generated one-sentence caption
   prepended and a `parent_id` link.
4. Full chunk metadata per `ARCHITECTURE.md` §7.1, including `content_hash`,
   `heading_path`, `section_path`, and `source_url`.
5. Snapshot builder producing `manifest.json`, `chunks.jsonl`, `parents.jsonl`,
   `rejected.jsonl`, and `checksums.txt`, with a content-addressed `snapshot_id` of
   the form `gov-a-<YYYYMMDD>-<hash12>`.
6. Hard validation gates: no chunk over 500 tokens; every chunk has non-null
   `source_url` and `tier`; every `parent_id` resolves.
7. First published snapshot from the 605 extracted documents.

| | |
|---|---|
| **Exit criteria** | A snapshot exists, validates clean, and rebuilds to an identical `snapshot_id` from the same inputs. Chunk-length distribution reviewed. A manual read of 20 randomly sampled chunks confirms each is self-contained and correctly attributed. |
| **Risks** | *Heading detection failure* on PDFs without clean structure produces one giant chunk per document — mitigated by monitoring the chunks-per-document distribution and flagging outliers. *Table captions that misdescribe their table* — mitigated by sampling captioned tables in review. *Chunker retune forces re-embedding* — mitigated by leaving `embedding` null in the snapshot (§6.3), making retune cheap until Phase 3 completes. |

---

## Phase 3 — Import, Embedding, and Dense Retrieval

**Owner: AI** · Collaborators: PL (migration sign-off)

First end-to-end retrieval. Deliberately single-retriever: no hybrid, no rerank.

| | |
|---|---|
| **Entry criteria** | Phase 2 exit met. Embedding model selected and its dimension known. |

**Deliverables**

1. Embedding model selected and pinned; `embedding vector(<dim>)` column migrated
   onto `document_chunks`.
2. Snapshot import management command: checksum verification, schema validation,
   transactional insert with `farm_id = NULL` and `index_key = 'gov_tier_a'`,
   embedding jobs enqueued, atomic activation only after all rows embed.
3. `corpus_snapshots` table with exactly one active row; rollback by pointer flip.
4. HNSW partial index for gov dense retrieval.
5. Dense retrieval path wired through `RetrievalScope` with the scope predicate in
   the SQL, returning top-k with parent expansion.
6. `POST /api/assistant/messages` returns a real, retrieved, cited answer for
   gov-corpus questions.
7. Idempotent re-import: importing the same snapshot twice changes nothing.

| | |
|---|---|
| **Exit criteria** | Every chunk from the active snapshot is embedded and searchable. A gov-corpus question returns an answer with resolvable citations carrying live `agriculture.gov.au` URLs. Audit records the `snapshot_id` and full version tuple. Import of a corrupted snapshot aborts without disturbing the active one. Cross-farm leak test passes with gov rows present. |
| **Risks** | *Embedding cost or time on 2,250 documents' worth of chunks* — mitigated by batching, resumable jobs, and running the first pass off the critical path. *Dimension change after migration* forces a full re-embed — mitigated by treating model selection as a gated decision before the migration. *Activation race* leaving a half-embedded snapshot live — mitigated by activating only after an embedding-completeness check. |

---

## Phase 4 — Hybrid Retrieval and Reranking

**Owner: AI**

The single highest-leverage quality phase. Do not skip the reranker.

| | |
|---|---|
| **Entry criteria** | Phase 3 exit met. Dense-only baseline metrics captured, even informally. |

**Deliverables**

1. `text_search` generated `tsvector` column plus GIN partial indexes for gov and
   tenant lexical recall.
2. Lexical recall path, tuned for the terms dense retrieval loses: chemical names,
   machinery model numbers, standard codes, cultivar names, dates.
3. Reciprocal Rank Fusion over dense top-50 and lexical top-50, with fusion weights
   in `retrieval_config_version`.
4. Cross-encoder reranking behind `RerankPort`, narrowing top-50 to top-8.
5. MMR diversity filtering to suppress near-duplicate chunks.
6. Context assembly: parent expansion, dedup by `content_hash`, token-budget
   packing that preserves source-class tags and per-class floors.
7. Graceful degradation, each flagged in both the response and the audit record:
   reranker unavailable falls back to fused order; dense unavailable falls back to
   lexical-only.

| | |
|---|---|
| **Exit criteria** | Hybrid plus rerank measurably beats the dense-only baseline on a held-out query set. Both degradation paths are tested and observably flagged. Retrieval latency stays within the §8 budget. Every retrieval stage writes candidate IDs and scores to the audit funnel. |
| **Risks** | *Reranker latency* pushes past the budget — mitigated by capping the rerank candidate set and measuring before adopting a larger model. *RRF weights tuned on too few queries* overfit — mitigated by deferring final tuning until Phase 7's gold set exists and treating Phase 4 weights as provisional. *Lexical recall dominated by boilerplate* — mitigated by Phase 1 boilerplate stripping landing first. |

---

## Phase 5 — Citations and Verification

**Owner: AI** · Collaborators: UI (rendering contract)

| | |
|---|---|
| **Entry criteria** | Phase 4 exit met. Citation display contract agreed with UI. |

**Deliverables**

1. Generation prompt template, registered in the prompt registry, emitting inline
   markers bound to a citation map, with the context-only constraint and an
   explicit facts-versus-general-guidance separation.
2. Citation resolution: every marker resolves to a chunk in the assembled context;
   an unresolvable marker is an error, not a warning.
3. Entailment verification behind `EntailmentPort`, scoring each cited claim
   against its cited chunk.
4. Failure handling: drop the claim, re-cite from another retrieved chunk, or
   downgrade that sub-claim — never ship an unsupported citation.
5. Content-addressed citation display so an expanded citation shows the exact chunk
   text the model saw.
6. Source-class tagging carried through to the response payload, distinguishing
   `gov_tier_a`, `gov_tier_b`, `tenant_document`, and `farm_record`.
7. Verifier-unavailable degradation: ship with markers resolved, confidence
   downgraded, and an explicit "not machine-verified" note.

| | |
|---|---|
| **Exit criteria** | Every factual sentence in a sampled response set is either cited or labelled general guidance. Citation-resolution and unciteable-claim tests pass. Entailment scores appear per claim in the audit record. UI renders expandable citations against the agreed contract. |
| **Risks** | *Model omits markers* under some phrasings — mitigated by structured output plus a post-check that treats an uncited factual sentence as a failure. *Entailment false negatives* strip correct claims — mitigated by calibrating the threshold against a labelled sample in Phase 7 and starting permissive. *Verification latency* — mitigated by batching claim checks and by the documented degradation path. |

---

## Phase 6 — Groundedness Gate and Refusals

**Owner: AI** · Collaborators: UI (refusal surfaces)

| | |
|---|---|
| **Entry criteria** | Phase 5 exit met. Refusal registry scaffolded from Phase 0. |

**Deliverables**

1. Three gate signals: retrieval confidence from the top reranker score, coverage
   across every part of a multi-part question, and cross-chunk conflict detection.
2. Decision policy producing `ANSWER`, `PARTIAL`, or `REFUSE`. A partial answer
   states explicitly what it could not cover rather than filling the gap from
   parametric knowledge.
3. Full refusal registry: `NO_RELEVANT_CONTEXT`, `INSUFFICIENT_COVERAGE`,
   `CONFLICTING_SOURCES`, `OUT_OF_SCOPE`, `ACCESS_DENIED`, `TENANT_SCOPE_EMPTY`,
   `PROVIDER_UNAVAILABLE`, each with an actionable user-facing template.
4. Fail-closed behaviour: any gate error yields `REFUSE`.
5. Conflict surfacing rather than silent selection, applying the §5.3 precedence
   order and citing both sides.
6. Safety and compliance responses carry a visible warning and request human
   verification.
7. Provisional thresholds, explicitly marked as uncalibrated pending Phase 7.

| | |
|---|---|
| **Exit criteria** | Every refusal path is reachable and tested. The gate-fails-closed test passes. A curated set of unanswerable questions is refused with the correct code and an actionable message. Gate scores and the decision reason appear in every audit record. |
| **Risks** | *Over-refusal* makes the assistant feel useless in demos — mitigated by starting permissive and tightening only with Phase 7 evidence. *Coverage scoring on multi-part questions* is the hardest signal to get right — mitigated by decomposing at the Understand stage so coverage is scored per part. *Conflict detection false positives* on chunks that merely differ in emphasis — mitigated by requiring material contradiction, not lexical difference. |

---

## Phase 7 — Evaluation Harness

**Owner: AI** · Collaborators: PL (review time), SCH (domain queries)

Build this before scaling anything. RAG quality degrades silently without it.

| | |
|---|---|
| **Entry criteria** | Phase 6 exit met. Domain reviewer time allocated. |

**Deliverables**

1. Gold query set of 100–300 labelled queries spanning gov-only, tenant-only,
   blended, operational, weather, and deliberately-unanswerable cases.
2. Retrieval metrics: Recall@k, MRR, nDCG.
3. Generation metrics: faithfulness/groundedness, answer relevance, citation
   precision and recall.
4. Refusal calibration: false-refusal rate against false-answer rate, plotted so an
   operating threshold is chosen deliberately rather than inherited.
5. Regression suite executed on every change to chunking, embedding, retrieval
   config, prompts, or the tool registry.
6. Version-tuple-aware result storage, so any two runs are comparable only when
   their tuples differ in exactly the element under test.
7. Calibrated gate thresholds replacing the Phase 6 provisional values.

| | |
|---|---|
| **Exit criteria** | The gold set exists and is reviewed. Baseline metrics are recorded for the current version tuple. CI fails on a regression beyond an agreed tolerance. Gate thresholds are calibrated from the refusal curve. |
| **Risks** | *Gold set too small* to detect real regressions — mitigated by the 100-query floor and by weighting toward the POC demo paths. *Labelling drift* between reviewers — mitigated by written labelling guidance and a double-labelled overlap sample. *Evaluation becomes a chore nobody runs* — mitigated by wiring it into CI rather than leaving it a manual script. |

---

## Phase 8 — Tier B Fallback

**Owner: AI**

| | |
|---|---|
| **Entry criteria** | Phase 7 exit met. Baseline metrics on Tier A alone recorded, so the fallback's effect is measurable. |

**Deliverables**

1. Tier B ingested through the same Phase 1–2 pipeline into a `gov-ab-*` snapshot,
   stored with `index_key = 'gov_tier_b'`.
2. Two-pass retrieval: query Tier A; only when the gate would report low confidence
   or insufficient coverage, re-query Tier A + B and re-rank once.
3. Tier B results carry a lower-confidence indicator through ranking, citation, and
   display.
4. Single-retry bound on the fallback, so latency stays predictable.
5. Evaluation of the fallback's effect on both false-refusal rate and citation
   precision.

| | |
|---|---|
| **Exit criteria** | Tier B never appears in a default-scope result. The fallback measurably reduces false refusals without degrading citation precision beyond tolerance. Fallback invocation is visible in the audit record. |
| **Risks** | *Tier B dilutes precision* if it leaks into the default index — mitigated by the `index_key` predicate and a test asserting Tier A-only default scope. *Latency doubles* on fallback queries — mitigated by the single-retry bound. *Fallback fires too often*, indicating a badly calibrated gate rather than a Tier A coverage gap — mitigated by tracking fallback rate as an SLO. |

---

## Phase 9 — Tenant Documents

**Owner: AI** · Collaborators: UI (upload and review surfaces), PL (schema)

The first phase where a mistake leaks private data. Everything here is
scope-first.

| | |
|---|---|
| **Entry criteria** | Phase 8 exit met. MinIO upload path working. Document status lifecycle (`uploaded` → `processing` → `ready` / `failed`) agreed. |

**Deliverables**

1. Event-driven ingestion: upload to MinIO, metadata and status in PostgreSQL, RQ
   job for extraction, chunking, and embedding, so a soil report is queryable in
   session rather than after a nightly reindex.
2. Tenant chunks written to `document_chunks` with a non-null `farm_id` and
   `index_key = 'tenant_doc'`; tenant HNSW and GIN partial indexes created.
3. Role-derived eligibility: owner scopes cover all active farm documents; worker
   scopes populate `allowed_document_ids` from farm-shared safety and procedure
   documents plus task-linked documents.
4. Hard `farm_id` predicate in the retrieval SQL, with the no-post-hoc-filtering
   static check enforced in CI.
5. `TENANT_SCOPE_EMPTY` refusal with an actionable, document-type-specific message.
6. PDF and text support including tabular PDFs. DOCX and OCR remain out.
7. Archival semantics: archived documents retain rows and audit trail but are
   excluded from every scope and from new candidate generation.
8. Extraction candidates generated as inert reviewable records that require
   approval before becoming structured data.

| | |
|---|---|
| **Exit criteria** | The cross-farm leak test passes with real tenant data in both farms. A worker principal cannot retrieve an owner-only document through any entry point, including fallback and empty-result paths. Archiving a document removes it from answers atomically. The Onboarding Demo Farm completes the real upload → extraction → candidate review → approval path through the browser, with no mocked step. |
| **Risks** | *Cross-farm leak* — the top risk in the project; mitigated by scope construction confined to Admit, mandatory predicates, partial indexes, and blocking tests. *Messy real uploads* extract poorly — mitigated by curated fixtures for demo predictability plus a visible failed status with manual retry. *Candidate quality* too low to be worth reviewing — mitigated by starting with the narrowest well-defined candidate types. |

---

## Phase 10 — Tools, Blended Composition, and Audit Hardening

**Owner: AI** · Collaborators: SCH (proposal request contract), UI (drafts, audit views)

| | |
|---|---|
| **Entry criteria** | Phase 9 exit met. Tool input/output contracts finalised and classified read versus draft. |

**Deliverables**

1. Read tools implemented and registered: farm context, tasks, approved rules,
   schedules, alerts, authorised document search, cached weather, and the
   controlled current-weather lookup. Each re-derives scope from the principal.
2. Proposal tools: draft a task, draft a task update, request a FarmFlow schedule
   proposal. None writes an active record.
3. Draft lifecycle `draft → confirmed / rejected / expired`, where only human
   confirmation writes durable task or task-update data.
4. Tools-before-generation orchestration: all selected tools complete before the
   generation stage; no model-driven tool loop.
5. Dual retrieval for blended questions — separate tenant-scoped and gov-scoped
   calls merged only at assembly, with source class preserved end to end.
6. Structured-outranks-prose precedence enforced, with disagreements surfaced and
   both sides cited rather than silently resolved.
7. Weather integration through the controlled tool: cached snapshots, `retrieved_at`
   surfaced, staleness warning past twelve hours, and no invented values when no
   usable snapshot exists.
8. Audit hardening: complete funnel capture, full version tuple, per-tool events,
   owner-only filtered read and export, append-only enforcement, and audit-write
   failure failing the request.
9. Replay capability: given an `audit_id`, reconstruct the version tuple and the
   serialised scope and re-execute retrieval against the pinned snapshot.

| | |
|---|---|
| **Exit criteria** | A blended question returns an answer citing both the farm's own document and Tier A guidance, visually distinguished. A structured-versus-document conflict surfaces both values with the structured one stated as operational truth. The assistant requests a schedule proposal without influencing placement, and the determinism test still passes. Replay of a past `audit_id` reproduces its retrieval result. All mandatory tests from `ARCHITECTURE.md` §13 pass. |
| **Risks** | *Tool sprawl* — mitigated by requiring a registry entry, a contract, and a test per tool. *Blended answers blurring source classes* — mitigated by per-class budget floors and the distinguishing display contract. *Assistant drifting into scheduling decisions* — mitigated by the determinism test and by the scheduler consuming only approved structured data. *Audit volume* — mitigated by storing concise structured metadata rather than raw content. |

---

## Phase 11+ — Deferred

Each deferred item has a written trigger. Nothing here starts on intuition; it
starts when its trigger fires and its owner confirms the evidence.

| Item | Trigger | Owner | Estimated effort |
|---|---|---|---|
| OCR for scanned and image-rendered PDFs | Phase 1 review shows a material share of the 34 empty extractions is recoverable content, **or** real tenant uploads are predominantly scanned | AI | Medium |
| Agentic / iterative retrieval | Evaluation shows multi-hop questions failing coverage that a bounded two-to-three-iteration loop demonstrably fixes | AI | Medium |
| Query decomposition | Multi-part questions show materially worse coverage scores than single-part questions on the gold set | AI | Small |
| Self-querying metadata filters | Users repeatedly express date, region, or document-type constraints in natural language that retrieval ignores | AI | Small |
| Qdrant migration from pgvector | pgvector recall or latency measurably fails the POC target and the documented comparison on retrieval quality, filtering, operations, cost, and deployment fit favours Qdrant | AI, PL | Large |
| External BM25 service | Postgres FTS demonstrably underperforms on exact-term recall in the gold set | AI | Medium |
| Photo and image captioning | A demo scenario requires image evidence and a captioning path can produce citeable, verifiable text | AI | Large |
| DOCX ingestion | Real onboarding data arrives predominantly as DOCX | AI | Small |
| Document versioning and supersession UX | A farm re-uploads an updated document type — typically soil tests — and stale answers are observed | AI, UI | Medium |
| Cross-session durable chat history | Client scope changes to require conversation recall beyond the session | AI | Medium |
| Manager and viewer roles | A POC scenario requires a permission level between owner and worker | PL | Small |
| Tier C cold index | A concrete question is provably answerable only from Tier C, and a human opt-in surface is justified | AI | Medium |
| Model-driven tool calling | Orchestrator-selected tools measurably mis-select on the gold set, and auditability of a model loop can be preserved | AI | Medium |
| External monitoring platform | Structured logs and `/healthz` prove insufficient during shared-demo instability | PL | Medium |
| Separate staging environment | The shared demo becomes too unstable for safe integration work | PL | Small |

Deferral is a decision, not a backlog. An item without a fired trigger is not
"coming later" — it is currently out of the system by design.

---

## Cross-Phase Gates

Gates apply to every phase from the one named onward. A phase does not exit with a
gate failing, regardless of feature completeness.

| Gate | From phase | Requirement | Verified by |
|---|---|---|---|
| **G1 — Scope integrity** | 0 | Every retrieval call takes a `RetrievalScope` built only in Admit. No retrieval entry point accepts a bare query string. | Static check plus scope-construction test |
| **G2 — No post-hoc filtering** | 0 | Scope predicates appear in SQL. No Python-side filtering of retrieval results by `farm_id`. | Static check in CI |
| **G3 — Cross-farm isolation** | 9 | A farm A principal never receives a farm B chunk under any path, including empty-result, fallback, and blended. | Blocking leak test |
| **G4 — Role eligibility** | 9 | A worker receives only farm-shared safety/procedure and task-linked documents. | Blocking test |
| **G5 — Audit completeness** | 0 | Every response carries an `audit_id` whose record contains the executed scope and the full version tuple. Audit-write failure fails the request. | Audit completeness test |
| **G6 — Version pinning** | 3 | The version tuple resolves once per request in Admit; no stage reads a different version mid-request. | Test plus code review |
| **G7 — Citation resolution** | 5 | Every inline marker resolves to a chunk in the assembled context. No uncited factual sentence ships unlabelled. | Citation and unciteable-claim tests |
| **G8 — Fail closed** | 6 | Gate errors and provider failures produce refusals or labelled degradations, never fabricated content. | Failure-injection tests |
| **G9 — Determinism preserved** | 0 | Identical approved inputs produce an identical schedule proposal. No model output reaches FarmFlow placement. | Determinism test, run every phase |
| **G10 — Idempotency** | 1 | Re-running any pipeline stage or background job produces no duplicates and no changed output. | Rerun tests for extraction, chunking, embedding, import, candidates |
| **G11 — Registry completeness** | 0 | Every tool, index, refusal code, and prompt is registered, documented, versioned, and reachable. | Registry completeness test |
| **G12 — No regression** | 7 | Gold-set metrics do not drop beyond the agreed tolerance for the version tuple under test. | Regression suite in CI |
| **G13 — Contract stability** | 0 | Response payload shape changes are additive within a phase, or are announced to UI a phase ahead. | OpenAPI diff review |
| **G14 — Snapshot integrity** | 3 | A corrupted or schema-invalid snapshot aborts import without touching the active snapshot. | Import failure test |

## Sequencing Summary

```text
Phase 0   Foundations and contracts                    AI  ── stub answers, real audit
Phase 1   Corpus extraction and filtering              AI  ── 639 → 605 clean, 34 reviewed
Phase 2   Chunking and snapshot build                  AI  ── gov-a-<date>-<hash>
Phase 3   Import, embedding, dense retrieval           AI  ── first real cited answer
Phase 4   Hybrid retrieval and reranking               AI  ── highest quality-per-effort
Phase 5   Citations and verification                   AI  ── no unciteable facts
Phase 6   Groundedness gate and refusals               AI  ── fail closed
Phase 7   Evaluation harness                           AI  ── stop flying blind
Phase 8   Tier B fallback                              AI  ── 1,054 docs, second pass only
Phase 9   Tenant documents                             AI  ── isolation is the whole phase
Phase 10  Tools, blended composition, audit hardening  AI  ── POC feature complete
Phase 11+ Deferred, trigger-gated                      varies
```

Phases 1 through 8 run entirely on the public corpus. Private data enters at
Phase 9, by which point scoping, gating, citation, and audit are already proven —
which is the point of the ordering.

## Related Records

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — normative architecture for this track
- `DesignDoc.md` — general multi-stage RAG pattern
- `FARMCORE_DOCS/architecture-decision-checklist.md` — running decision log
- `FARMCORE_DOCS/skeleton-readiness-checklist.md` — implementation skeleton readiness
- `FARMCORE_DOCS/system-shape.md` — runtime and module boundaries
- `docs/adr/` — architecture decision records
