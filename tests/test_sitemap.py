from scraper.sitemap import parse_robots_for_sitemaps, parse_sitemap_xml


def test_parse_robots_for_sitemaps() -> None:
    robots_text = """
    User-agent: *
    Allow: /
    Sitemap: https://example.com/sitemap.xml
    Sitemap: /sitemap-news.xml
    """

    result = parse_robots_for_sitemaps(robots_text, "https://example.com")

    assert result == [
        "https://example.com/sitemap.xml",
        "https://example.com/sitemap-news.xml",
    ]


def test_parse_sitemap_index() -> None:
    xml_text = """
    <sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
      <sitemap><loc>https://example.com/sitemap-a.xml</loc></sitemap>
      <sitemap><loc>https://example.com/sitemap-b.xml</loc></sitemap>
    </sitemapindex>
    """

    parsed = parse_sitemap_xml(xml_text)

    assert parsed.kind == "sitemapindex"
    assert parsed.locations == [
        "https://example.com/sitemap-a.xml",
        "https://example.com/sitemap-b.xml",
    ]


def test_parse_urlset() -> None:
    xml_text = """
    <urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
      <url><loc>https://example.com/page-1</loc></url>
      <url><loc>https://example.com/page-2</loc></url>
    </urlset>
    """

    parsed = parse_sitemap_xml(xml_text)

    assert parsed.kind == "urlset"
    assert parsed.locations == [
        "https://example.com/page-1",
        "https://example.com/page-2",
    ]
