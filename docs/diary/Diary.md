# Engineering Diary — FarmCore AI/RAG Track (`RAG_docs`)

Append-only. Newest day first. Format: `docs/DOCUMENTATION_STANDARDS.md` (Diary section).

Entry types: `FAILURE` · `DECISION` · `PROGRESS` · `BLOCKED` · `MEASUREMENT` · `NOTE`

---

## 2026-08-27 (Thu)

### PROGRESS — SOTA documentation set written

Shipped the enterprise documentation baseline for the Assistant & Knowledge track:

| Path | Role |
|---|---|
| `docs/ARCHITECTURE.md` | System shape, trust boundaries, what is NOT in RAG |
| `docs/PLAN.md` | Phases 0–10 + Phase 11+ deferrals |
| `docs/API.md` | Nine API groups, error model, ownership matrix |
| `docs/EXTENSIBILITY.md` | Ports, registries, extension checklists |
| `docs/MAPPING.md` | DesignDoc → FarmCore → Phase → P0/P1/P2 |
| `docs/DOCUMENTATION_STANDARDS.md` | ADR/Diary templates, CI doc gates |
| `docs/adr/0001`–`0010` | Accepted architecture decisions |
| `docs/openapi/openapi.design.yaml` | Phase 0 design-time OpenAPI (v0.4.0) |
| `Diary.md` | This file |

Next step: Phase 0 contract freeze — stub endpoints + UI/SCH review of `docs/API.md`.

### DECISION — DesignDoc stays SOTA; POC downscopes are explicit ADRs

Compared `DesignDoc.md` to `FARMCORE_DOCS`. DesignDoc is a superset of the FarmCore POC RAG bar. Kept hybrid + rerank + groundedness + claim citations. Downscoped via ADRs: pgvector (0001), Postgres FTS (0002), one-table logical indexes (0003), LLM-as-judge not NLI (0005), Tier C never indexed (0008).

### DECISION — Assistant never places FarmFlow tasks

Scheduling boundary is contracts only: `POST /api/assistant/schedule-explanations` and rule-candidate drafts. Writes to schedules/rules stay with the Scheduling team. ADR-0006.

### MEASUREMENT — Corpus at doc freeze

| Metric | Value | Source |
|---|---|---|
| Inventory / library plan | 4,704 | `data/manifests/*` |
| Tier A / B / C | 2,250 / 1,054 / 1,268 | `farm_ai_tiers.md` |
| Tier A source PDFs | 639 | `tier_a_pdf_text.jsonl` |
| Extracted / empty / failed | 605 / 34 / 0 | same |
| On-disk success docs | 4,572 | pdf_library (fetched+skipped) |

### PROGRESS — Tier A PDF text extraction

```text
Targets 639 · Extracted 605 · Empty 34 · Failed 0
Output: data/text/source/… + data/manifests/tier_a_pdf_text.jsonl
```

34 empties are likely scanned/image PDFs (OCR deferred to Phase 11).

### DECISION — PDF layout: `data/pdf/source/` vs rendered

Genuine downloaded PDFs live under `data/pdf/source/`; WeasyPrint HTML→PDF under `data/pdf/rendered/`. Text for RAG prefers `data/text/` (HTML) and `data/text/source/` (PDF extracts).

---

## 2026-08-26 (Wed) — *(backfilled 2026-08-27)*

### PROGRESS — Tier A/B/C classification

`farm_ai_tiers.md` (14,913 lines): A default index, B second-pass fallback, C archive excluded. ADR-0008.

### FAILURE — WeasyPrint segfault under parallel workers

**Symptom.** `fetch-library --workers 8` then `--workers 2` died with exit 139 (SIGSEGV). No Python traceback. Progress stopped mid `rendered_pdf` (plant pest pages).

**Environment.** macOS arm64, Python 3.11 venv, WeasyPrint → Cairo/Pango, ThreadPoolExecutor.

**Root cause.** Native rendering stack is not safe under concurrent threads even with a Python render lock; long runs amplify native-heap pressure.

**Resolution.** Resume with `--workers 1`. Fetch of PDF/Office stayed fine; HTML→PDF serialised. Final run: EXIT 0; 3,096 rendered / 836 source PDFs / 640 office; 132 HTTP failures (403/404).

**Prevention.** Do not parallelise WeasyPrint on threads. Prefer process isolation or serial render. Heartbeat logs so segfault ≠ hang.

### FAILURE — Cloudflare blocked plain httpx discover on DPIRD

**Symptom.** `discover` for `dpird.nsw.gov.au` returned empty sitemaps; httpx got 403 HTML challenges.

**Resolution.** agriculture.gov.au inventory (this corpus) works with Chrome UA via `config.agriculture.yaml`. Sitemap-first discovery preferred over blind link crawl. Browser fallback needed for harder CF sites; Chromium XML viewer wrapping still breaks raw XML parse — separate issue.

**Prevention.** Probe with real browser UA; assert minimum inventory size; sitemap-first for gov sites.

---

## 2026-08-25 (Tue) — *(backfilled 2026-08-27)*

### PROGRESS — Repo bootstrap

Created `.venv` (Python 3.11; system 3.9 cannot install crawl4ai≥0.9.2). Installed `requirements.txt`, Playwright Chromium, `crawl4ai-setup`. Copied `config.example.yaml` → `config.yaml`. Scaffolded `scraper/` stages writing JSONL manifests under `data/manifests/` for resumability.

### DECISION — Manifest-per-stage pipeline

Every ingest stage reads/writes JSONL rather than in-memory-only state. Cost: intermediate files. Benefit: crash resume, diffs, audit. Same instinct as FarmCore per-stage document status and immutable corpus snapshots (ADR-0009).
