from pathlib import Path

from scraper.corpus_filter import (
    REASON_EMPTY_EXTRACTION,
    doc_title_for,
    is_untitled_title,
    strip_boilerplate,
    text_path_for_library_row,
    text_similarity,
    token_count,
)


def test_token_count_basic() -> None:
    assert token_count("one two three") == 3


def test_untitled_detection() -> None:
    assert is_untitled_title("Untitled document")
    assert is_untitled_title("untitled")
    assert not is_untitled_title("Drought assistance overview")


def test_doc_title_from_breadcrumb() -> None:
    title = doc_title_for(
        {
            "topic_breadcrumb": ["Drought", "Farm Support"],
            "filename": "report.pdf",
        }
    )
    assert title == "Farm Support"


def test_boilerplate_strip_removes_repeated_short_lines() -> None:
    pages = []
    for index in range(4):
        pages.append(
            f"Skip to main content\n"
            f"Real policy paragraph about drought section {index}.\n"
            f"Footer line"
        )
    text = "\n\n".join(pages)
    cleaned = strip_boilerplate(text)
    assert "Skip to main content" not in cleaned
    assert "Footer line" not in cleaned
    assert "drought" in cleaned.lower()


def test_near_duplicate_similarity_high() -> None:
    a = "Drought assistance is available for eligible farm businesses in Australia."
    b = "Drought assistance is available for eligible farm businesses in Australia!"
    assert text_similarity(a, b) >= 0.9


def test_empty_extraction_reason_constant() -> None:
    assert REASON_EMPTY_EXTRACTION == "EMPTY_EXTRACTION"


def test_text_path_for_rendered_html_row() -> None:
    row = {
        "library_kind": "rendered_pdf",
        "local_path": "data/pdf/rendered/agriculture.gov.au/abares/products/citations.pdf",
    }
    output_dir = Path(__file__).resolve().parents[2] / "data"
    path = text_path_for_library_row(row, output_dir)
    assert path == output_dir / "text/agriculture.gov.au/abares/products/citations.txt"
