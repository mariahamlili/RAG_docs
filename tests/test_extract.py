from scraper.extract import extract_document


def test_extract_document_returns_title_and_text() -> None:
    html = """
    <html>
      <head><title>Fallback Title</title></head>
      <body>
        <header>Navigation</header>
        <main>
          <h1>Animal Welfare Guide</h1>
          <p>Keep livestock hydrated and sheltered.</p>
        </main>
      </body>
    </html>
    """

    result = extract_document(html, "https://example.com/guide")

    assert result.title == "Animal Welfare Guide"
    assert "Keep livestock hydrated and sheltered." in result.text
    assert "Source: https://example.com/guide" in result.cleaned_html
