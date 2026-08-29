# RAG_docs — FarmCore Corpus & Assistant Monorepo

This repository has **two cooperating tracks** for Australian agriculture RAG:

| Track | Folder | What it does |
|---|---|---|
| **Corpus ingest** | [`ingest/`](ingest/) | Download, organise, and extract text from `agriculture.gov.au` (and similar sites) |
| **Assistant runtime** | [`farmcore/`](farmcore/) | Django API, retrieval contracts, audit, stub chat (`CAI-001+`) |
| **Shared contracts** | [`shared/`](shared/) | Schemas both tracks must agree on (e.g. `chunks-v1`) |
| **Corpus on disk** | [`data/`](data/) | PDFs, text, manifests (large dirs; see `data/README.md`) |
| **Documentation** | [`docs/`](docs/) | Architecture, API, ADRs, sprint plan, product notes |

```text
RAG_docs/
├── README.md                 ← you are here
├── docker-compose.yml        ← FarmCore stack (Postgres, Redis, MinIO, web, worker)
├── pytest.ini
├── config.yaml               ← local ingest config (gitignored; copy from ingest/config/)
│
├── ingest/                   ← OFFLINE corpus pipeline (no FarmCore DB access)
│   ├── README.md
│   ├── requirements.txt
│   ├── config/               ← example YAML templates
│   ├── scraper/              ← Python package: discover → fetch → extract
│   └── tests/
│
├── farmcore/                 ← ONLINE assistant / documents Django app
│   ├── README.md
│   ├── requirements.txt
│   ├── manage.py
│   ├── accounts/ farms/ documents/ assistant/ scheduling/
│   └── tests/
│
├── shared/
│   └── schemas/              ← chunks-v1 JSON schema + validator
│
├── data/
│   ├── manifests/            ← JSONL inventories, tier lists (in git)
│   ├── pdf/ office/ text/ raw/  ← bulky corpus (local; may be in git)
│   └── README.md
│
└── docs/
    ├── README.md             ← documentation index
    ├── ARCHITECTURE.md PLAN.md API.md …   ← CAI / assistant contracts
    ├── adr/ openapi/
    ├── diary/                ← engineering diary
    ├── design/               ← original RAG pattern reference
    └── product/              ← FarmCore product working notes
```

## Quick start — corpus ingest

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r ingest/requirements.txt
playwright install chromium
cp ingest/config/example.yaml config.yaml   # or ingest/config/agriculture.yaml

PYTHONPATH=ingest python -m scraper.main discover \
  --root-url "https://www.agriculture.gov.au" --config config.yaml
```

See [`ingest/README.md`](ingest/README.md) for `plan-library`, `fetch-library`, and PDF text extraction.

## Quick start — FarmCore assistant (Phase 0 stub)

```bash
docker compose up --build
# API: http://localhost:8000/api/assistant/messages
```

Or local SQLite: see [`farmcore/README.md`](farmcore/README.md).

## Tests

```bash
pip install -r ingest/requirements.txt -r farmcore/requirements.txt
pytest
```

## Documentation map

| Need | Start here |
|---|---|
| System design & trust boundaries | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Build phases & exit criteria | [`docs/PLAN.md`](docs/PLAN.md) |
| API contracts | [`docs/API.md`](docs/API.md) |
| 4-week CAI tickets | [`docs/CAI_SPRINT_PLAN.md`](docs/CAI_SPRINT_PLAN.md) |
| Engineering log | [`docs/diary/Diary.md`](docs/diary/Diary.md) |
| Product / team notes | [`docs/product/`](docs/product/) |

## Boundary rule

`ingest/` **never** connects to the FarmCore database. Handoff is an immutable
**snapshot** (`chunks.jsonl` + manifest) imported by FarmCore in later phases.
