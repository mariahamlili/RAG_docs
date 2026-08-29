"""Extract text from Tier A source PDFs into data/text/source/."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pymupdf
import typer
from rich.console import Console
from rich.table import Table

from scraper.config import AppConfig
from scraper.farm_tiers import is_tier_a

app = typer.Typer(help="Extract text from Farm AI Tier A source PDFs.")
console = Console()


def text_path_for_pdf(pdf_path: Path, output_dir: Path) -> Path:
    """Map data/pdf/source/.../file.pdf → data/text/source/.../file.txt"""
    parts = pdf_path.parts
    try:
        idx = parts.index("pdf")
        # pdf/source/... → text/source/...
        relative = Path(*parts[idx + 1 :])
    except ValueError:
        relative = Path("source") / pdf_path.name
    return output_dir / "text" / relative.with_suffix(".txt")


def extract_pdf_text(pdf_path: Path) -> str:
    parts: list[str] = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            text = page.get_text("text")
            if text and text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts).strip()


@app.command("extract-tier-a-pdfs")
def extract_tier_a_pdfs(
    config: Path = typer.Option(Path("config.agriculture.yaml"), help="Config YAML."),
    library_path: Path = typer.Option(
        Path("data/manifests/pdf_library.jsonl"),
        help="Library manifest to select Tier A source PDFs from.",
    ),
    resume: bool = typer.Option(True, help="Skip PDFs that already have a non-empty text file."),
    min_chars: int = typer.Option(40, help="Below this, mark as empty extraction."),
) -> None:
    app_config = AppConfig.load(config)
    app_config.ensure_directories()
    if not library_path.exists():
        raise typer.BadParameter(f"Library manifest not found: {library_path}")

    rows = [
        json.loads(line)
        for line in library_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    targets = []
    for row in rows:
        if row.get("status") not in {"fetched", "skipped"}:
            continue
        if row.get("library_kind") != "source_pdf":
            continue
        if not is_tier_a(row.get("topic_path") or ""):
            continue
        pdf_path = Path(row.get("local_path") or "")
        if not pdf_path.exists():
            continue
        targets.append(row)

    stats = Counter()
    results: list[dict] = []

    for index, row in enumerate(targets, start=1):
        pdf_path = Path(row["local_path"])
        out_path = text_path_for_pdf(pdf_path, app_config.output_dir)
        console.print(f"[{index}/{len(targets)}] {pdf_path}")

        if resume and out_path.exists() and out_path.stat().st_size > 0:
            stats["skipped"] += 1
            results.append(
                {
                    **row,
                    "local_text_path": str(out_path),
                    "text_status": "skipped",
                    "text_chars": out_path.stat().st_size,
                }
            )
            continue

        try:
            text = extract_pdf_text(pdf_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if len(text) < min_chars:
                stats["empty"] += 1
                out_path.write_text(text, encoding="utf-8")
                results.append(
                    {
                        **row,
                        "local_text_path": str(out_path),
                        "text_status": "empty",
                        "text_chars": len(text),
                    }
                )
                continue

            out_path.write_text(text, encoding="utf-8")
            stats["extracted"] += 1
            results.append(
                {
                    **row,
                    "local_text_path": str(out_path),
                    "text_status": "extracted",
                    "text_chars": len(text),
                }
            )
        except Exception as exc:  # noqa: BLE001 - batch job should continue
            stats["failed"] += 1
            results.append(
                {
                    **row,
                    "text_status": "failed",
                    "error": str(exc),
                }
            )

    out_manifest = app_config.output_dir / "manifests" / "tier_a_pdf_text.jsonl"
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    with out_manifest.open("w", encoding="utf-8") as handle:
        for row in results:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Patch local_text_path onto pdf_library rows for Tier A PDFs we handled.
    by_url = {
        row["source_url"]: row
        for row in results
        if row.get("local_text_path") and row.get("text_status") in {"extracted", "skipped", "empty"}
    }
    updated = []
    for row in rows:
        patch = by_url.get(row.get("source_url"))
        if patch:
            row = {**row, "local_text_path": patch["local_text_path"]}
        updated.append(row)
    with library_path.open("w", encoding="utf-8") as handle:
        for row in updated:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    table = Table(title="Tier A PDF Text Extraction")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Targets", str(len(targets)))
    table.add_row("Extracted", str(stats["extracted"]))
    table.add_row("Skipped", str(stats["skipped"]))
    table.add_row("Empty", str(stats["empty"]))
    table.add_row("Failed", str(stats["failed"]))
    table.add_row("Manifest", str(out_manifest))
    console.print(table)


if __name__ == "__main__":
    app()
