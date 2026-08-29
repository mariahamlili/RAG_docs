import json
from pathlib import Path


def test_tier_a_extraction_baseline_605_34() -> None:
    """CAI-021: extraction baseline must not regress without an intentional tooling change."""
    path = Path("data/manifests/tier_a_pdf_text.jsonl")
    assert path.exists(), "Run extract-tier-a-pdfs before this test"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    status = {row.get("text_status") for row in rows}
    extracted = sum(1 for row in rows if row.get("text_status") == "extracted")
    empty = sum(1 for row in rows if row.get("text_status") == "empty")
    failed = sum(1 for row in rows if row.get("text_status") == "failed")
    assert len(rows) == 639
    assert extracted == 605, f"expected 605 extracted, got {extracted}"
    assert empty == 34, f"expected 34 empty, got {empty}"
    assert failed == 0
    assert status <= {"extracted", "empty", "skipped"}
