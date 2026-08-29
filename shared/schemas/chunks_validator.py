"""Standalone chunks-v1 validator (CAI-007)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

SCHEMA_VERSION = "chunks-v1"
DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent / "chunks-v1.schema.json"


def load_schema(path: Path | None = None) -> dict[str, Any]:
    schema_path = path or DEFAULT_SCHEMA_PATH
    with schema_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_chunk(record: dict[str, Any], *, schema_path: Path | None = None) -> None:
    schema = load_schema(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(record), key=lambda e: e.path)
    if errors:
        raise ValidationError(errors[0].message)


def validate_chunks_jsonl(path: Path, *, schema_path: Path | None = None) -> int:
    count = 0
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            try:
                validate_chunk(record, schema_path=schema_path)
            except ValidationError as exc:
                raise ValidationError(f"line {line_no}: {exc.message}") from exc
            count += 1
    return count
