from scraper.organize import (
    collapse_small_folders,
    filename_for,
    library_kind_for,
    topic_path_for,
)


def test_topic_path_for_assets_uses_discovered_from() -> None:
    topic = topic_path_for(
        "https://www.agriculture.gov.au/sites/default/files/documents/fmd-statistics-october2019.pdf",
        source_type="asset:pdf",
        discovered_from=(
            "https://www.agriculture.gov.au/agriculture-land/farm-food-drought/drought/fmd/statistics"
        ),
    )
    assert topic[0] == "drought-and-farm-support"
    assert "farm-management-deposits" in topic
    assert topic[-1] == "statistics"


def test_topic_path_for_html_uses_page_path() -> None:
    topic = topic_path_for(
        "https://www.agriculture.gov.au/agriculture-land/animal/welfare",
        source_type="html",
        discovered_from="https://www.agriculture.gov.au/",
    )
    assert topic == ("animal-welfare",)


def test_topic_path_bmsb_mapping() -> None:
    topic = topic_path_for(
        "https://www.agriculture.gov.au/sites/default/files/documents/x.pdf",
        source_type="asset:pdf",
        discovered_from="https://www.agriculture.gov.au/bmsb",
    )
    assert topic == ("biosecurity", "brown-marmorated-stink-bug")


def test_filename_fmd_date_normalization() -> None:
    name = filename_for(
        "https://example.com/documents/fmd-statistics-october2019.pdf",
        extension=".pdf",
    )
    assert name == "fmd-statistics-2019-10.pdf"


def test_filename_collision_appends_hash() -> None:
    taken: set[str] = set()
    first = filename_for(
        "https://example.com/a/report.pdf",
        extension=".pdf",
        content_hash="abcdef123456",
        taken=taken,
    )
    second = filename_for(
        "https://example.com/b/report.pdf",
        extension=".pdf",
        content_hash="abcdef123456",
        taken=taken,
    )
    assert first == "report.pdf"
    assert second == "report-abcdef12.pdf"


def test_filename_numeric_stem_uses_topic_leaf() -> None:
    name = filename_for(
        "https://example.com/documents/36411.pdf",
        extension=".pdf",
        topic_leaf="biotechnology",
    )
    assert name == "biotechnology-36411.pdf"


def test_collapse_small_folders_merges_singletons() -> None:
    assignments = [
        (("drought-and-farm-support", "stats"), "https://a/1.pdf"),
        (("drought-and-farm-support", "stats"), "https://a/2.pdf"),
        (("drought-and-farm-support", "stats"), "https://a/3.pdf"),
        (("drought-and-farm-support", "lonely"), "https://a/4.pdf"),
    ]
    collapsed = collapse_small_folders(assignments, min_files=3)
    assert collapsed["https://a/1.pdf"] == ("drought-and-farm-support", "stats")
    assert collapsed["https://a/4.pdf"] == ("drought-and-farm-support",)


def test_library_kind_for() -> None:
    assert library_kind_for("html") == "rendered_pdf"
    assert library_kind_for("asset:pdf") == "source_pdf"
    assert library_kind_for("asset:docx") == "office"
