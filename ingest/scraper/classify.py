from __future__ import annotations

from urllib.parse import urlsplit

ASSET_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".csv",
    ".zip",
}


def classify_url(url: str) -> str:
    path = urlsplit(url).path.lower()
    for extension in ASSET_EXTENSIONS:
        if path.endswith(extension):
            return f"asset:{extension[1:]}"
    return "html"


def is_pdf_asset(url: str) -> bool:
    return urlsplit(url).path.lower().endswith(".pdf")
