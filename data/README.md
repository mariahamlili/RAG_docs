# Data directory

On-disk corpus produced by [`../ingest/`](../ingest/). FarmCore imports **snapshots**
from processed chunks — it does not read this tree directly at runtime (except
during offline snapshot build in later CAI phases).

## Layout

```text
data/
├── manifests/          ← tracked in git (inventories, plans, tier classifications)
│   ├── agriculture_full_inventory.jsonl
│   ├── pdf_library.jsonl
│   ├── library_plan.jsonl
│   ├── farm_ai_tiers.md
│   └── tier_a_pdf_text.jsonl
│
├── pdf/
│   ├── source/         ← real downloaded PDFs (mirrored URL hierarchy)
│   ├── rendered/       ← WeasyPrint HTML→PDF
│   └── _rejected/      ← failed fetches
│
├── office/             ← DOCX, XLSX, PPTX
├── text/               ← trafilatura HTML text
│   └── source/         ← PyMuPDF Tier A PDF extracts
├── raw/                ← raw HTML fetch bodies
└── logs/               ← pipeline run logs (gitignored)
```

## Tier classification

| Tier | Count (approx.) | Use in FarmCore |
|---|---|---|
| A | 2,250 | Default gov index |
| B | 1,054 | Fallback only (Phase 8+) |
| C | 1,268 | Never indexed |

Source: `manifests/farm_ai_tiers.md`

## Regenerating

From repo root:

```bash
PYTHONPATH=ingest python -m scraper.main fetch-library --config config.yaml --workers 1 --resume
PYTHONPATH=ingest python -m scraper.extract_pdf_text
```

## Size

Full agriculture.gov.au library is **~3 GB** on disk. Clone may be large if corpus
was pushed to the remote.
