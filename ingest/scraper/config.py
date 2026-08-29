from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    user_agent: str = "RAGSiteIngestBot/0.1 (+contact@example.com)"
    request_timeout: int = 30
    request_delay_seconds: float = 1.5
    max_retries: int = 3
    verify_ssl: bool = True
    html_backend: str = "httpx"
    use_browser_fallback: bool = True
    headless_browser: bool = True
    crawl4ai_magic: bool = True
    follow_subdomains: bool = False
    allowed_schemes: list[str] = Field(default_factory=lambda: ["https"])
    ignored_query_prefixes: list[str] = Field(
        default_factory=lambda: ["utm_", "fbclid", "gclid", "mc_"]
    )
    output_dir: Path = Path("data")
    sitemap_candidates: list[str] = Field(
        default_factory=lambda: [
            "/sitemap.xml",
            "/sitemap_index.xml",
            "/sitemap-index.xml",
            "/sitemap/sitemap.xml",
            "/sitemap1.xml",
        ]
    )

    @classmethod
    def load(cls, path: str | Path | None) -> "AppConfig":
        if path is None:
            return cls()
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)

    def ensure_directories(self) -> dict[str, Path]:
        base_dir = self.output_dir
        directories = {
            "base": base_dir,
            "raw": base_dir / "raw",
            "text": base_dir / "text",
            "pdf": base_dir / "pdf",
            "logs": base_dir / "logs",
            "manifests": base_dir / "manifests",
        }
        for directory in directories.values():
            directory.mkdir(parents=True, exist_ok=True)
        return directories

    def dump(self) -> dict[str, Any]:
        data = self.model_dump()
        data["output_dir"] = str(self.output_dir)
        return data
