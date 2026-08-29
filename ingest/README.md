# Corpus ingest pipeline

Offline pipeline that builds the government document library for FarmCore RAG.
Runs **outside** the Django app and writes files under `../data/`.

## What it does

1. **Discover** — find sitemaps from `robots.txt` and common paths  
2. **Inventory** — expand sitemaps to a deduplicated URL list  
3. **Ingest** — fetch HTML/PDF/Office, extract text, render HTML→PDF  
4. **Organise** — `plan-library` / `fetch-library` with topic-based paths  
5. **Extract** — Tier A PDF text → `data/text/source/`
6. **Filter** — Tier A source PDFs + HTML pages (`rendered_pdf`), empty/untitled/near-dup filters, boilerplate strip → `data/text/clean/` (CAI-014–017, 020)

## Setup

```bash
cd ..   # repo root
python3 -m venv .venv && source .venv/bin/activate
pip install -r ingest/requirements.txt
playwright install chromium
crawl4ai-setup   # optional, for crawl4ai HTML backend

cp ingest/config/example.yaml config.yaml
# or: cp ingest/config/agriculture.yaml config.yaml
```

All commands use `PYTHONPATH=ingest` so the `scraper` package resolves:

```bash
export PYTHONPATH=ingest

python -m scraper.main discover \
  --root-url "https://www.agriculture.gov.au" --config config.yaml

python -m scraper.main plan-library --config config.yaml
python -m scraper.main fetch-library --config config.yaml --workers 1 --resume

python -m scraper.extract_pdf_text

python -m scraper.main filter-corpus --config config.yaml
```

## Layout

| Path | Role |
|---|---|
| `scraper/` | Python package (CLI entry: `scraper.main`) |
| `config/` | Example YAML configs (copy to repo-root `config.yaml`) |
| `tests/` | Unit tests for sitemap, organise, extract |

## Outputs (under `../data/`)

| Directory | Contents |
|---|---|
| `manifests/` | JSONL inventories, `pdf_library.jsonl`, tier lists |
| `pdf/source/` | Downloaded PDFs |
| `pdf/rendered/` | HTML→PDF renders |
| `office/` | DOCX/XLSX/PPTX |
| `text/` | HTML-extracted text |
| `text/source/` | PDF-extracted text (Tier A) |
| `text/clean/` | Boilerplate-stripped text (accepted corpus) |
| `raw/` | Raw HTML responses |

Quality manifests after `filter-corpus`: `rejected.jsonl`, `corpus_accepted.jsonl`, `extraction_quality_report.json`, `empty_extractions_review.md`, `near_duplicate_review_sample.jsonl`.

See [`../data/README.md`](../data/README.md).

## Tests

```bash
pytest ingest/tests -q
```
