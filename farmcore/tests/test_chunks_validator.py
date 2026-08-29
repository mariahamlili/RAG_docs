import pytest
from jsonschema.exceptions import ValidationError

from shared.schemas.chunks_validator import validate_chunk


def test_valid_chunk_record_passes():
    record = {
        "schema_version": "chunks-v1",
        "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
        "parent_id": None,
        "document_id": None,
        "index_key": "gov_tier_a",
        "tier": "A",
        "doc_title": "Drought assistance overview",
        "source_url": "https://www.agriculture.gov.au/drought",
        "heading_path": ["Support"],
        "section_path": "Support/Overview",
        "chunk_index": 0,
        "token_count": 120,
        "content_hash": "a" * 64,
        "text": "Drought assistance is available for eligible farm businesses.",
        "embedding": None,
    }
    validate_chunk(record)


def test_chunk_over_500_tokens_fails():
    record = {
        "schema_version": "chunks-v1",
        "chunk_id": "550e8400-e29b-41d4-a716-446655440001",
        "parent_id": None,
        "document_id": None,
        "index_key": "gov_tier_a",
        "tier": "A",
        "doc_title": "Too long",
        "source_url": "https://www.agriculture.gov.au/example",
        "heading_path": [],
        "section_path": "",
        "chunk_index": 0,
        "token_count": 501,
        "content_hash": "b" * 64,
        "text": "x",
        "embedding": None,
    }
    with pytest.raises(ValidationError):
        validate_chunk(record)
