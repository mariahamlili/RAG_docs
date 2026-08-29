# FarmCore Django skeleton (CAI-001–010)

Phase 0 foundation: contracts, ports, registries, audit, and stub assistant API.

## Quick start (Docker)

```bash
docker compose up --build
```

Services: **web** (:8000), **db** (Postgres + pgvector), **redis**, **minio** (:9000/:9001), **worker** (RQ).

Dev user (created on first boot): `owner` / `owner`  
Demo farm slug: `demo-farm`

## Quick start (local SQLite)

```bash
cd farmcore
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py bootstrap_dev
python manage.py runserver
```

## Stub API smoke test

```bash
# Login and set active farm in session (use browser admin or test client)
curl -X POST http://localhost:8000/api/assistant/messages \
  -H 'Content-Type: application/json' \
  -b cookies.txt -c cookies.txt \
  -d '{"message":"What is drought assistance?"}'
```

See `farmcore/tests/` for automated coverage.

## Tests

From repo root:

```bash
pip install -r ingest/requirements.txt -r farmcore/requirements.txt
pytest
```
