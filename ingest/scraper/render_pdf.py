from __future__ import annotations

from pathlib import Path


def render_html_to_pdf(html: str, output_path: Path, base_url: str) -> None:
    try:
        from weasyprint import HTML
    except OSError as exc:
        raise RuntimeError(
            "WeasyPrint system libraries are missing. Install pango and gdk-pixbuf before rendering PDFs."
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=base_url).write_pdf(str(output_path))
