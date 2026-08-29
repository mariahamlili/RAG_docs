from __future__ import annotations

from dataclasses import dataclass
from html import escape

import trafilatura
from bs4 import BeautifulSoup


@dataclass
class ExtractedDocument:
    title: str
    text: str
    cleaned_html: str


def _fallback_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for node in soup.select("script, style, noscript"):
        node.decompose()
    return "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())


def _title_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)
    return "Untitled document"


def _wrap_clean_html(title: str, body_html: str, source_url: str) -> str:
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <title>{title}</title>
    <style>
      @page {{ size: A4; margin: 18mm 14mm 18mm 14mm; }}
      body {{ font-family: Georgia, serif; font-size: 11pt; line-height: 1.55; color: #202124; }}
      h1, h2, h3 {{ color: #0c3b5d; }}
      a {{ color: #0c5a87; text-decoration: none; }}
      img {{ max-width: 100%; height: auto; }}
      .source {{ margin-top: 2rem; font-size: 9pt; color: #5f6368; }}
    </style>
  </head>
  <body>
    {body_html}
    <p class=\"source\">Source: {source_url}</p>
  </body>
</html>
"""


def _body_fragment(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    body = soup.body
    if body is None:
        return html
    return "".join(str(node) for node in body.contents)


def extract_document(html: str, source_url: str) -> ExtractedDocument:
    title = _title_from_html(html)
    text = trafilatura.extract(
        html,
        url=source_url,
        output_format="txt",
        include_links=False,
        include_images=True,
        favor_precision=True,
    )
    cleaned_html = trafilatura.extract(
        html,
        url=source_url,
        output_format="html",
        include_links=True,
        include_images=True,
        favor_precision=True,
    )

    final_text = text.strip() if text else _fallback_text(html)
    if cleaned_html:
        body_html = _body_fragment(cleaned_html.strip())
    else:
        body_html = f"<h1>{escape(title)}</h1><pre>{escape(final_text)}</pre>"

    body_html = _wrap_clean_html(title, body_html, source_url)

    return ExtractedDocument(title=title, text=final_text, cleaned_html=body_html)
