"""Extract text for all Tier A library assets (PDF, rendered HTML/PDF, office)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from scraper.config import AppConfig
from scraper.farm_tiers import corpus_tier, index_key_for_tier, is_corpus_eligible
from scraper.tier_a_text import MIN_CHARS_EMPTY, extract_for_row, text_output_path

app = typer.Typer(help="Extract Tier A text for all library kinds.")
console = Console()


def run_tier_a_extraction(
    *,
    app_config: AppConfig,
    library_path: Path,
    resume: bool = True,
    min_chars: int = MIN_CHARS_EMPTY,
) -> dict[str, int | str]:
    app_config.ensure_directories()

    rows = [
        json.loads(line)
        for line in library_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    targets = [
        row
        for row in rows
        if row.get("status") in {"fetched", "skipped"}
        and row.get("library_kind") in {"source_pdf", "rendered_pdf", "office"}
        and is_corpus_eligible(row.get("topic_path") or "")
        and row.get("local_path")
        and Path(row["local_path"]).exists()
    ]

    stats: Counter[str] = Counter()
    results: list[dict] = []

    for index, row in enumerate(targets, start=1):
        kind = row["library_kind"]
        console.print(f"[{index}/{len(targets)}] {kind}: {row.get('local_path')}")

        tier = corpus_tier(row.get("topic_path") or "")
        if not tier:
            continue

        try:
            out_path = text_output_path(row, app_config.output_dir)
        except Exception as exc:  # noqa: BLE001
            stats["failed"] += 1
            results.append(
                {
                    **row,
                    "farm_ai_tier": tier,
                    "index_key": index_key_for_tier(tier),
                    "text_status": "failed",
                    "error": str(exc),
                }
            )
            continue

        if resume and out_path.exists() and out_path.stat().st_size > 0:
            text = out_path.read_text(encoding="utf-8", errors="replace")
            if len(text.split()) >= 50:
                stats["skipped"] += 1
                results.append(
                    {
                        **row,
                        "farm_ai_tier": tier,
                        "index_key": index_key_for_tier(tier),
                        "local_text_path": str(out_path),
                        "text_status": "skipped",
                        "text_chars": len(text),
                        "extraction_method": "existing",
                    }
                )
                continue

        try:
            text, method, out_path = extract_for_row(row, app_config.output_dir)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text, encoding="utf-8")

            if len(text) < min_chars:
                stats["empty"] += 1
                status = "empty"
            else:
                stats["extracted"] += 1
                status = "extracted"

            stats[method] += 1
            results.append(
                {
                    **row,
                    "farm_ai_tier": tier,
                    "index_key": index_key_for_tier(tier),
                    "local_text_path": str(out_path),
                    "text_status": status,
                    "text_chars": len(text),
                    "extraction_method": method,
                }
            )
        except Exception as exc:  # noqa: BLE001
            stats["failed"] += 1
            results.append(
                {
                    **row,
                    "farm_ai_tier": tier,
                    "index_key": index_key_for_tier(tier),
                    "text_status": "failed",
                    "error": str(exc),
                }
            )

    out_manifest = app_config.output_dir / "manifests" / "farm_corpus_text.jsonl"
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    with out_manifest.open("w", encoding="utf-8") as handle:
        for row in results:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

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

    table = Table(title="Farm corpus text extraction (Tier A + curated Tier B)")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Targets", str(len(targets)))
    table.add_row("Extracted", str(stats["extracted"]))
    table.add_row("Skipped", str(stats["skipped"]))
    table.add_row("Empty", str(stats["empty"]))
    table.add_row("Failed", str(stats["failed"]))
    table.add_row("Manifest", str(out_manifest))
    console.print(table)

    return {
        "targets": len(targets),
        "extracted": stats["extracted"],
        "skipped": stats["skipped"],
        "empty": stats["empty"],
        "failed": stats["failed"],
        "manifest": str(out_manifest),
    }


@app.command("extract-all")
def extract_all(
    config: Path = typer.Option(Path("config.yaml"), help="Config YAML."),
    library_path: Path = typer.Option(Path("data/manifests/pdf_library.jsonl"), help="Library manifest."),
    resume: bool = typer.Option(True, help="Skip rows with existing non-empty text."),
    min_chars: int = typer.Option(MIN_CHARS_EMPTY, help="Below this, mark as empty."),
) -> None:
    app_config = AppConfig.load(config)
    run_tier_a_extraction(
        app_config=app_config,
        library_path=library_path,
        resume=resume,
        min_chars=min_chars,
    )


if __name__ == "__main__":
    app()
