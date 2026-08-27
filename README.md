# RAG Site Ingest

A sitemap-first website ingestion pipeline for building RAG-ready documents.

This project is designed for sites that publish XML sitemaps and may protect direct HTTP access with Cloudflare or similar bot mitigation. It discovers sitemap URLs, expands nested sitemap indexes, normalizes and deduplicates page URLs, classifies assets, downloads content politely, extracts clean text, renders cleaned HTML pages to PDF, and writes a manifest for downstream RAG chunking.

## Features

- Discover sitemap entry points from `robots.txt` and common sitemap paths.
- Expand sitemap indexes, nested sitemaps, and `.xml.gz` sitemap files.
- Normalize URLs and strip common tracking parameters.
- Classify HTML pages versus existing file assets such as PDF and DOCX.
- Fetch with retries, rate limiting, and browser fallback via Playwright.
- Optional `crawl4ai` backend for browser-led, RAG-oriented HTML ingestion.
- Extract clean text and simplified HTML using `trafilatura`.
- Render cleaned HTML to PDF using `WeasyPrint`.
- Save a JSONL manifest for PDFs, extracted text, and crawl metadata.

## Project layout

```text
rag_site_ingest/
  config.example.yaml
  requirements.txt
  scraper/
    main.py
    config.py
    fetch.py
    sitemap.py
    classify.py
    extract.py
    render_pdf.py
    manifest.py
    utils.py
  tests/
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

To use the `crawl4ai` HTML backend, its own setup command is recommended after install:

```bash
crawl4ai-setup
```

## Quick start

1. Copy `config.example.yaml` to `config.yaml` and adjust values.
2. Discover sitemaps.
3. Build the URL inventory.
4. Ingest a sample set before running the full site.

```bash
python -m scraper.main discover --root-url "https://www.dpird.nsw.gov.au" --config config.yaml
python -m scraper.main inventory --root-url "https://www.dpird.nsw.gov.au" --config config.yaml
python -m scraper.main ingest --root-url "https://www.dpird.nsw.gov.au" --config config.yaml --limit 10
```

To try the `crawl4ai` backend, set `html_backend: crawl4ai` in `config.yaml` and run the same ingest command.

## Commands

### Discover sitemap entry points

```bash
python -m scraper.main discover --root-url "https://www.dpird.nsw.gov.au" --config config.yaml
```

Writes a sitemap manifest to `data/manifests/sitemaps.json`.

### Expand sitemaps into a normalized URL inventory

```bash
python -m scraper.main inventory --root-url "https://www.dpird.nsw.gov.au" --config config.yaml
```

Writes a JSONL inventory to `data/manifests/url_inventory.jsonl`.

### Ingest pages and assets

```bash
python -m scraper.main ingest --root-url "https://www.dpird.nsw.gov.au" --config config.yaml --limit 50
```

Outputs:

- `data/raw/`: raw HTTP responses and copied assets
- `data/text/`: extracted text files
- `data/pdf/`: rendered or copied PDFs
- `data/manifests/documents.jsonl`: RAG-oriented metadata manifest

## Notes for Cloudflare-protected sites

The target domain currently blocks plain command-line HTTP requests with a Cloudflare challenge. This project therefore supports a browser fallback using Playwright. For some sites you may still need to run Chromium non-headless or reuse browser state/cookies if the site applies stronger protection.

When `html_backend` is set to `crawl4ai`, HTML pages are fetched through `crawl4ai`'s browser crawler while sitemap XML and binary assets continue to use the lighter direct fetch path.

## RAG workflow after ingestion

The pipeline stops at document generation plus manifest creation. The next stage should chunk the text files, attach chunk metadata, and feed them into your embedding and vector database workflow.

## Test

```bash
pytest
```
