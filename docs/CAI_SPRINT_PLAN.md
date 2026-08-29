# CAI Sprint Plan — RAG Track (4 Weeks)

Weekly ticket backlog for the **Corpus & Assistant Intelligence (CAI)** track only.
Scheduling (FarmFlow writes, rule placement, determinism) is **out of scope** until
Week 4 integration stubs. Ticket IDs use the **`CAI-`** prefix.

Companion records: [`PLAN.md`](PLAN.md) · [`ARCHITECTURE.md`](ARCHITECTURE.md) ·
[`API.md`](API.md) · **Trackers:** [Google Sheet](https://docs.google.com/spreadsheets/d/162oSO9W9aEn3YUu2PD70VbgczyalacavalhlCEo7rsU/edit?gid=2052173087#gid=2052173087) · [`CAI_SPRINT_PLAN.xlsx`](CAI_SPRINT_PLAN.xlsx)

Sync command (updates xlsx/csv; add `--google` with service-account creds for Sheets):

```bash
pip install -r scripts/requirements.txt
python scripts/sync_cai_sprint_sheet.py          # local xlsx + csv
python scripts/sync_cai_sprint_sheet.py --google # push to Google Sheet
```

Edit **Completion** / **Blockers** in [`cai_sprint_tracker.json`](cai_sprint_tracker.json), then re-run sync.

## Document Metadata

| Field | Value |
|---|---|
| Title | CAI 4-Week RAG Sprint Plan |
| Status | **Draft** |
| Date | 2026-08-28 |
| Owning team | Assistant / Documents (AI) |
| Ticket prefix | `CAI-` |
| Horizon | 4 weeks — end-to-end gov-corpus RAG POC |
| Out of scope (Wks 1–3) | Scheduling writes, FarmFlow placement, rule authoring |
| Week 4 only | Chat ↔ scheduling **integration placeholders** (descriptions; implement if time) |

## How to Use This Document

1. Pull tickets into your tracker as `CAI-###` (copy title + description).
2. Respect **Depends** — gates from [`PLAN.md`](PLAN.md) apply even if a ticket is “small”.
3. **Size**: `S` ≤ 0.5 day · `M` 1–2 days · `L` 3–5 days · `XL` multi-day / risky.
4. Items marked **Done (pre-sprint)** reflect work already in `RAG_docs`; still verify exit criteria.
5. Week 4 scheduling tickets are **optional integration** — do not block RAG demo exit.

## Sprint Goal (Week 4 exit)

A farm owner can ask a **gov-corpus question** in chat and receive a **cited,
gate-checked answer** backed by the Tier A snapshot, with audit replay. Optional:
tenant document upload + blended answer. Optional: scheduling read/draft hooks wired
for a joint demo with the Scheduling team.

---

## Corpus Baseline (already measured)

| Metric | Value | Relevant tickets |
|---|---|---|
| Tier A docs | 2,250 | CAI-020+ |
| Tier A source PDFs | 639 | CAI-015 (partial) |
| Extracted / empty | 605 / 34 | CAI-015, CAI-018 |
| On-disk library | 4,572 docs | — |

---

## Week 1 — Foundations + Corpus Quality

**Theme:** Contracts frozen, skeleton running, Tier A text clean and reviewed.  
**Maps to:** PLAN Phase 0 + Phase 1  
**Week exit:** Stub `POST /api/assistant/messages` returns schema-valid refusal + audit;
605 clean Tier A texts; `rejected.jsonl` complete; quality report signed off.

| ID | Title | Size | Depends | Description / acceptance |
|---|---|---|---|---|
| **CAI-001** | Confirm FarmCore repo + Compose stack boots | M | — | ✅ `docker-compose.yml` + `farmcore/` |
| **CAI-002** | Scaffold Django apps (`accounts`, `farms`, `documents`, `assistant`, `scheduling`) | M | CAI-001 | ✅ |
| **CAI-003** | Agree `document_chunks` schema on paper | M | CAI-002 | ✅ `shared/schemas/document_chunks.md` + model |
| **CAI-004** | Implement `RetrievalScope` dataclass + validation | M | CAI-003 | ✅ `assistant/scope.py` |
| **CAI-005** | Declare port interfaces + no-op adapters | M | CAI-003 | ✅ `assistant/ports/` |
| **CAI-006** | Scaffold four registries + version constants | S | CAI-005 | ✅ `assistant/registries/` |
| **CAI-007** | Define `chunks-v1` schema + standalone validator | M | CAI-003 | ✅ `shared/schemas/chunks-v1.schema.json` |
| **CAI-008** | Audit event schema + `VersionTuple` + migration | M | CAI-002 | ✅ `assistant/models.py` + `versions.py` |
| **CAI-009** | OpenAPI design freeze with UI team | S | — | ✅ `docs/OPENAPI_FREEZE.md` (UI sign-off pending) |
| **CAI-010** | Stub `POST /api/assistant/messages` E2E | L | CAI-004, CAI-008, CAI-009 | ✅ `POST /api/assistant/messages` |
| **CAI-011** | CI: scope-integrity + cross-farm leak test skeletons | M | CAI-010 | ✅ `tests/farmcore/` (14 tests) |
| **CAI-012** | Pin extraction tooling in `requirements.txt` | S | — | ✅ `pymupdf` pinned in `ingest/requirements.txt`. |
| **CAI-013** | **Done (pre-sprint)** Tier A PDF text extraction | — | CAI-012 | ✅ 605 extracted, 34 empty, 0 failed → `data/text/source/`, `tier_a_pdf_text.jsonl`. |
| **CAI-014** | Tier A manifest filter (`TIER_EXCLUDED`) | S | CAI-013 | ✅ `ingest/scraper/corpus_filter.py` + `filter-corpus` CLI → `rejected.jsonl` (197 non–Tier A). |
| **CAI-015** | Pre-chunk filters: empty + untitled | M | CAI-014 | ✅ `EMPTY_EXTRACTION` (<50 tok), `LIKELY_NON_TEXT_ASSET` (untitled + <100 tok). |
| **CAI-016** | Near-duplicate detection + pointer | M | CAI-015 | ✅ Similarity ≥0.9 → reject with `kept_doc_id` (4 pairs found). |
| **CAI-017** | Boilerplate stripper | M | CAI-015 | ✅ Repeated short lines + nav blocklist → `data/text/clean/`. |
| **CAI-018** | Manual review: 34 empty extractions | M | CAI-013 | ✅ All 34 `ocr_recoverable` — `empty_extractions_review.md` + `.jsonl` + OCR probe |
| **CAI-019** | Manual review: 30-doc near-dup sample | S | CAI-016 | ✅ 4/4 pairs confirmed — `near_duplicate_review.md` |
| **CAI-020** | Extraction quality report | M | CAI-015–017 | ✅ `data/manifests/extraction_quality_report.json` + `.md`. |
| **CAI-021** | CI assertion: 605/34 extraction split | S | CAI-013, CAI-020 | ✅ `ingest/tests/test_extraction_baseline.py`. |

**Week 1 buffer / if ahead:** start CAI-022 (chunker design doc) or tighten CAI-010 response schema for citations field (empty array).

---

## Week 2 — Chunking, Snapshot, First Retrieval

**Theme:** Immutable gov snapshot built; embeddings live; dense-only answers work.  
**Maps to:** PLAN Phase 2 + Phase 3  
**Week exit:** `gov-a-*` snapshot validates; import + embed complete; gov question returns
real cited answer (dense-only OK); `snapshot_id` in audit.

| ID | Title | Size | Depends | Description / acceptance |
|---|---|---|---|---|
| **CAI-022** | Structure-aware chunker (headings → paragraphs) | L | CAI-017, CAI-007 | 300–500 tok, ~15% overlap within section; never split table mid-row; never cross heading. |
| **CAI-023** | Parent-child chunk hierarchy | M | CAI-022 | Children embedded/matched; parents for generation; every child has resolvable `parent_id`. |
| **CAI-024** | Table chunks with captions | M | CAI-022 | Separate chunks; one-sentence caption prepended; `parent_id` link. |
| **CAI-025** | Chunk metadata completeness | M | CAI-022 | `content_hash`, `heading_path`, `section_path`, `source_url`, `tier` on every chunk. |
| **CAI-026** | Snapshot builder CLI | L | CAI-023–025 | Outputs `manifest.json`, `chunks.jsonl`, `parents.jsonl`, `rejected.jsonl`, `checksums.txt`; `snapshot_id = gov-a-<YYYYMMDD>-<hash12>`. |
| **CAI-027** | Snapshot validation gates | M | CAI-026 | Hard-fail: no chunk >500 tok; non-null `source_url` + `tier`; all `parent_id` resolve. |
| **CAI-028** | Publish first Tier A snapshot | M | CAI-027 | From 605 clean docs; idempotent rebuild → identical `snapshot_id`. |
| **CAI-029** | Sample review: 20 random chunks | S | CAI-028 | Manual read confirms self-contained, correctly attributed chunks. |
| **CAI-030** | Select + pin embedding model | M | CAI-028 | Model chosen; dimension documented; cost/latency estimate for full corpus. |
| **CAI-031** | Migrate `embedding vector(dim)` on `document_chunks` | M | CAI-030, CAI-003 | Migration applied; gov rows `farm_id = NULL`, `index_key = 'gov_tier_a'`. |
| **CAI-032** | Snapshot import management command | L | CAI-028, CAI-031 | Checksum verify, schema validate, transactional insert, embed jobs enqueued, activate only when 100% embedded. |
| **CAI-033** | `corpus_snapshots` table + atomic activation | M | CAI-032 | Exactly one active row; rollback = pointer flip. |
| **CAI-034** | HNSW partial index (gov dense) | M | CAI-031 | Partial index for `index_key = 'gov_tier_a'`; query plan checked. |
| **CAI-035** | Dense retrieval path via `RetrievalScope` | L | CAI-004, CAI-034 | SQL scope predicate; top-k + parent expansion; no post-hoc Python farm filter. |
| **CAI-036** | Wire generation to retrieved context | L | CAI-035, CAI-005 | `POST /api/assistant/messages` returns real answer for gov-only questions (markers optional this week). |
| **CAI-037** | Idempotent re-import test | S | CAI-032 | Same snapshot twice → no duplicate rows, no partial state. |
| **CAI-038** | Cross-farm leak test with gov rows | M | CAI-035 | Tenant query cannot return gov rows mis-scoped; gov query cannot leak farm data. |
| **CAI-039** | Import corrupted snapshot abort test | S | CAI-032 | Bad checksum → active snapshot unchanged. |
| **CAI-040** | Audit: record `snapshot_id` + version tuple | S | CAI-036 | Every assistant response audit row includes pinned snapshot. |

**Week 2 stretch:** basic retrieval debug endpoint behind feature flag (API §6 preview).

---

## Week 3 — Hybrid Quality, Citations, Gate, Eval Start

**Theme:** Production-quality retrieval path; trustworthy citations; refuse when unsure;
gold set started.  
**Maps to:** PLAN Phase 4 + Phase 5 + Phase 6 + Phase 7 (start)  
**Week exit:** Hybrid+rereank beats dense baseline informally; every factual sentence
cited or labelled guidance; refusal paths tested; 50+ gold queries drafted.

| ID | Title | Size | Depends | Description / acceptance |
|---|---|---|---|---|
| **CAI-041** | `tsvector` column + GIN partial indexes | M | CAI-035 | Postgres FTS for gov (and tenant partial stub if schema ready). |
| **CAI-042** | Lexical recall path | M | CAI-041 | Tuned for codes, chemical names, dates, machinery IDs. |
| **CAI-043** | RRF fusion (dense-50 + lexical-50) | M | CAI-042 | Weights in `retrieval_config_version`; audit logs stage scores. |
| **CAI-044** | `RerankPort` + cross-encoder integration | L | CAI-043 | Top-50 → top-8; latency measured against §8 budget. |
| **CAI-045** | MMR diversity filter | M | CAI-044 | Suppress near-duplicate chunks in final context. |
| **CAI-046** | Context assembly + token budget | M | CAI-045 | Parent expansion, dedup by `content_hash`, source-class floors. |
| **CAI-047** | Degradation paths (rerank / dense down) | M | CAI-044 | Reranker down → fused order; dense down → lexical-only; flagged in response + audit. |
| **CAI-048** | Capture dense-only baseline metrics | S | CAI-035 | Informal Recall@10 on 20 queries before hybrid merge. |
| **CAI-049** | Prompt registry: citation marker template | M | CAI-036 | Context-only constraint; facts vs general guidance separation. |
| **CAI-050** | Citation resolution + error on orphan markers | M | CAI-049 | Every `[n]` resolves to assembled chunk; unresolvable = hard error. |
| **CAI-051** | `EntailmentPort` + per-claim scoring | L | CAI-050 | Score cited claims; drop/re-cite/downgrade unsupported claims. |
| **CAI-052** | Citation display payload (content-addressed) | M | CAI-050 | UI contract: expanded citation shows exact chunk text model saw. Agree with UI. |
| **CAI-053** | Source-class tags in response | S | CAI-052 | `gov_tier_a` distinguished in payload (tenant classes stubbed). |
| **CAI-054** | Gate signals: confidence, coverage, conflict | L | CAI-046 | Three signals implemented; provisional thresholds documented. |
| **CAI-055** | Gate policy: ANSWER / PARTIAL / REFUSE | M | CAI-054 | Partial states what was not covered; no parametric gap-fill. |
| **CAI-056** | Refusal registry (full codes) | M | CAI-006 | `NO_RELEVANT_CONTEXT`, `INSUFFICIENT_COVERAGE`, `CONFLICTING_SOURCES`, `OUT_OF_SCOPE`, `ACCESS_DENIED`, `TENANT_SCOPE_EMPTY`, `PROVIDER_UNAVAILABLE` + templates. |
| **CAI-057** | Fail-closed gate behaviour | S | CAI-055 | Any gate error → `REFUSE`; tested. |
| **CAI-058** | Refusal path integration tests | M | CAI-056–057 | Curated unanswerable set returns correct code + message. |
| **CAI-059** | Audit: retrieval funnel + per-claim entailment | M | CAI-043, CAI-051 | Candidate IDs, scores, gate decision reason on every request. |
| **CAI-060** | Draft gold query set (50 queries) | M | CAI-048 | Gov-only, unanswerable, multi-part; labelling guide written. |
| **CAI-061** | Expand gold set to 100+ queries | M | CAI-060 | Domain reviewer pass; double-label overlap sample. |
| **CAI-062** | Eval script: retrieval metrics | M | CAI-061 | Recall@k, MRR, nDCG offline runner. |
| **CAI-063** | Eval script: generation + citation metrics | M | CAI-061 | Faithfulness, citation precision/recall skeleton. |

**Week 3 stretch:** HyDE query rewrite behind flag (P1); UI renders expandable citations in chat.

---

## Week 4 — Eval Hardening, E2E Demo, Integration Hooks

**Theme:** Regression-safe RAG POC demo; optional tenant upload; **scheduling
integration tickets only** (mostly descriptions / thin stubs).  
**Maps to:** PLAN Phase 7 (+ Phase 9/10 slices) + cross-team integration  
**Week exit:** CI eval regression gate; demo script runs gov Q&A with citations;
audit replay works; scheduling hooks documented or stubbed for joint demo.

### RAG core (required)

| ID | Title | Size | Depends | Description / acceptance |
|---|---|---|---|---|
| **CAI-064** | Wire eval suite into CI | M | CAI-062–063 | Fails on regression beyond agreed tolerance. |
| **CAI-065** | Calibrate gate thresholds from refusal curve | M | CAI-061, CAI-054 | Replace provisional Phase 6 thresholds with evidence-based values. |
| **CAI-066** | Version-tuple-aware eval result storage | M | CAI-064 | Compare runs only when tuple element under test differs. |
| **CAI-067** | Audit replay: retrieval re-execution | L | CAI-059 | Given `audit_id`, reconstruct tuple + scope; re-run retrieval against pinned snapshot. |
| **CAI-068** | Tier B fallback (optional P1) | L | CAI-065 | Two-pass A then A+B; single retry; `index_key` predicate tests. Skip if Week 3 slipped. |
| **CAI-069** | Tenant doc upload → MinIO → RQ job (optional) | L | CAI-033 | PDF/text only; `farm_id` set; `index_key = tenant_doc`. Skip if time-constrained. |
| **CAI-070** | Blended retrieval: tenant + gov separate calls | M | CAI-069 | Merge at assembly only; source classes preserved. Depends on CAI-069. |
| **CAI-071** | Cross-farm leak test with real tenant data | M | CAI-069 | Blocking test with two farms; worker vs owner scopes. |
| **CAI-072** | E2E demo script + checklist | M | CAI-036, CAI-052 | 5 gov questions, 2 refusals, 1 conflict (if available); audit export sample. |
| **CAI-073** | Operational runbook | S | CAI-072 | Re-embed, snapshot rollback, provider outage, eval rerun commands. |
| **CAI-074** | Diary + PLAN status update | S | CAI-072 | Record metrics, thresholds, known gaps, Phase 11+ triggers fired. |

### Chat ↔ Scheduling integration (Week 4 only — optional / stub)

> **Not required for RAG POC exit.** Implement only for joint demo with Scheduling.
> Assistant **never writes** schedules or placements (ADR-0006).

| ID | Title | Size | Depends | Description (implement if time) |
|---|---|---|---|---|
| **CAI-075** | Read tool: `get_farm_context` | S | CAI-006 | Returns farm metadata + role; re-derives scope from principal. No scheduling logic. |
| **CAI-076** | Read tool: `list_tasks` / `list_schedules` (read-only) | M | CAI-075 | Calls Scheduling read APIs; structured JSON for orchestrator; audit per tool call. |
| **CAI-077** | `POST /api/assistant/schedule-explanations` stub | M | CAI-010 | Accepts schedule snapshot + question; returns explanation draft **without** mutating schedule. Contract aligned with Scheduling team. |
| **CAI-078** | Proposal tool: `draft_task` (no write) | M | CAI-006 | Creates `draft` record only; owner confirmation required to persist. **No feasibility check in this ticket.** |
| **CAI-079** | Proposal tool: `request_schedule_proposal` (no placement) | M | CAI-077 | Assistant requests Scheduling-generated proposal; assistant explains result; does not influence FarmFlow determinism. |
| **CAI-080** | Orchestration: tools-before-generation | M | CAI-076–079 | Fixed tool set runs before LLM; no model-driven tool loop in POC. |
| **CAI-081** | **Deferred** `evaluate_task_feasibility` read tool | — | CAI-078 | *Description only.* Calls `POST /api/task-feasibility-evaluations` (Scheduling-owned). Returns feasible / better-time / infeasible for **hypothetical** task fields. Chat shows guidance; no schedule write. Phase 11+ unless demo requires it. |
| **CAI-082** | **Deferred** Chat flow: draft → feasibility → confirm | — | CAI-081 | *Description only.* Owner describes work in chat; assistant drafts task, runs feasibility read, surfaces confirmation UI. Scheduling owns evaluation logic. |
| **CAI-083** | Joint demo: blended farm doc + gov guidance + schedule explain | M | CAI-070, CAI-077 | Single scripted path for show-and-tell with UI + SCH present. |

---

## Ticket Summary by Week

| Week | Focus | Ticket range | Approx. count | Hard exit |
|---|---|---|---|---|
| 1 | Foundations + corpus | CAI-001 – CAI-021 | 21 | Stub API + clean Tier A text |
| 2 | Chunk + embed + dense RAG | CAI-022 – CAI-040 | 19 | Real gov answers (dense) |
| 3 | Hybrid + cite + gate + eval | CAI-041 – CAI-063 | 23 | Cited, gated answers; gold set |
| 4 | Eval CI + demo + integration | CAI-064 – CAI-083 | 20 | Demo + replay; SCH stubs optional |

**Total: 83 tickets** (6 pre-done / deferred-description only).

---

## Critical Path (do not parallelise blindly)

```text
CAI-001 → CAI-010 → CAI-028 → CAI-032 → CAI-036
                ↘ CAI-015–020 (corpus, parallel)
CAI-036 → CAI-043 → CAI-050 → CAI-055 → CAI-064 → CAI-072
```

---

## Risk Register (sprint-level)

| Risk | Week | Mitigation ticket |
|---|---|---|
| Contract churn blocks UI | 1 | CAI-009, CAI-010 |
| Near-dup collapses annual reports | 1 | CAI-019 |
| Chunker produces 1 chunk/doc | 2 | CAI-029 distribution check |
| Embedding cost / time | 2 | CAI-030, CAI-032 batching |
| Reranker latency over budget | 3 | CAI-044, CAI-047 |
| Over-refusal in demo | 3–4 | CAI-065 calibration |
| Scope leak when tenant added | 4 | CAI-071 |
| Scheduling scope creep | 4 | CAI-075–083 marked optional; ADR-0006 |

---

## Definition of Done (per ticket)

- Code merged with tests (or manifest artifact for pipeline tickets).
- Audit behaviour verified where applicable.
- [`docs/diary/Diary.md`](diary/Diary.md) entry for `L`/`XL` tickets or any FAILURE/DECISION.
- Depends tickets closed before moving to downstream work.

---

## Changelog

| Date | Change |
|---|---|
| 2026-08-28 | Initial 4-week CAI sprint plan created from PLAN Phases 0–7 + Week 4 integration slice |
