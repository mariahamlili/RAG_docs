from pathlib import Path

from scraper.classify import classify_url
from scraper.utils import extract_internal_links, normalize_url, path_from_url, slug_from_url


def test_normalize_url_strips_tracking_params() -> None:
    normalized = normalize_url(
        "https://example.com/path/?utm_source=x&id=1#frag",
        ["utm_", "fbclid", "gclid"],
    )

    assert normalized == "https://example.com/path?id=1"


def test_slug_from_url_is_stable() -> None:
    slug = slug_from_url("https://example.com/path/to/page?id=1")

    assert slug == "example-com-path-to-page-id-1"


def test_classify_url_detects_pdf() -> None:
    assert classify_url("https://example.com/file.pdf") == "asset:pdf"
    assert classify_url("https://example.com/page") == "html"


def test_extract_internal_links_filters_scope_and_duplicates() -> None:
        html = """
        <html>
            <body>
                <a href="/about">About</a>
                <a href="https://example.com/about?utm_source=test">About again</a>
                <a href="sub/page">Subpage</a>
                <a href="#top">Top</a>
                <a href="mailto:test@example.com">Email</a>
                <a href="https://other.example.org/ignore">Other site</a>
            </body>
        </html>
        """

        links = extract_internal_links(
                html,
                page_url="https://example.com/start/",
                root_url="https://example.com",
                ignored_prefixes=["utm_"],
                follow_subdomains=False,
        )

        assert links == [
                "https://example.com/about",
                "https://example.com/start/sub/page",
        ]

def test_path_from_url_mirrors_hierarchy() -> None:
    base = Path("/out")
    assert path_from_url("https://www.agriculture.gov.au/", base, ".pdf") == Path("/out/agriculture.gov.au/index.pdf")
    assert path_from_url("https://www.agriculture.gov.au/abares", base, ".pdf") == Path("/out/agriculture.gov.au/abares.pdf")
    assert path_from_url("https://www.agriculture.gov.au/abares/research-topics/agricultural-outlook", base, ".pdf") == Path("/out/agriculture.gov.au/abares/research-topics/agricultural-outlook.pdf")
    assert path_from_url("https://www.agriculture.gov.au/abares/research-topics/agricultural-outlook", base, ".txt") == Path("/out/agriculture.gov.au/abares/research-topics/agricultural-outlook.txt")
    # Drupal asset paths are flattened to documents/
    assert path_from_url("https://www.agriculture.gov.au/sites/default/files/documents/report.pdf", base, ".pdf") == Path("/out/agriculture.gov.au/documents/report.pdf")