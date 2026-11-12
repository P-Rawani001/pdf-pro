"""Local settings, recent files persistence, and safe atomic file operations."""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import (
    OLLAMA_DEFAULT_MODEL,
    RECENT_FILES_PATH,
    SETTINGS_PATH,
    ensure_app_directories,
)

logger = logging.getLogger("pdf_pro.file_service")


@dataclass
class RecentFileEntry:
    """Metadata stored for a recently opened PDF."""

    path: str
    name: str
    page_count: int
    last_opened: str


class FileService:
    """Manages recent files, app settings, and safe temporary/atomic writes."""

    MAX_RECENT_FILES = 20

    def __init__(self) -> None:
        ensure_app_directories()

    def load_settings(self) -> dict[str, Any]:
        """Load local user preferences with safe defaults."""
        defaults: dict[str, Any] = {
            "theme": "dark",
            "default_zoom": 1.0,
            "ollama_model": OLLAMA_DEFAULT_MODEL,
            "right_panel_visible": True,
        }
        if not SETTINGS_PATH.exists():
            return defaults
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                defaults.update(data)
        except Exception as exc:
            logger.warning("Failed to read settings.json, using defaults: %s", exc)
        return defaults

    def save_settings(self, settings: dict[str, Any]) -> None:
        """Atomically persist user preferences to disk."""
        self._atomic_write_text(SETTINGS_PATH, json.dumps(settings, indent=2))

    def get_recent_files(self) -> list[RecentFileEntry]:
        """Return existing recent PDFs ordered from newest to oldest."""
        if not RECENT_FILES_PATH.exists():
            return []
        try:
            raw = json.loads(RECENT_FILES_PATH.read_text(encoding="utf-8"))
            entries: list[RecentFileEntry] = []
            for item in raw:
                p = Path(item.get("path", ""))
                if p.exists() and p.is_file():
                    entries.append(
                        RecentFileEntry(
                            path=str(p.resolve()),
                            name=item.get("name", p.name),
                            page_count=int(item.get("page_count", 0)),
                            last_opened=item.get("last_opened", ""),
                        )
                    )
            return entries
        except Exception as exc:
            logger.warning("Could not parse recent_files.json: %s", exc)
            return []

    def add_recent_file(self, file_path: Path | str, page_count: int = 0) -> None:
        """Record or bump a PDF in the recent files list."""
        resolved = Path(file_path).resolve()
        entries = [
            e for e in self.get_recent_files() if Path(e.path).resolve() != resolved
        ]
        entries.insert(
            0,
            RecentFileEntry(
                path=str(resolved),
                name=resolved.name,
                page_count=page_count,
                last_opened=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            ),
        )
        trimmed = [asdict(e) for e in entries[: self.MAX_RECENT_FILES]]
        self._atomic_write_text(RECENT_FILES_PATH, json.dumps(trimmed, indent=2))

    def clear_recent_files(self) -> None:
        """Clear saved recent files history."""
        self._atomic_write_text(RECENT_FILES_PATH, "[]")

    @staticmethod
    def create_temp_pdf_path(prefix: str = "pdfpro_") -> Path:
        """Create a unique temporary PDF path in the OS temp folder."""
        fd, temp_name = tempfile.mkstemp(prefix=prefix, suffix=".pdf")
        os.close(fd)
        return Path(temp_name)

    @staticmethod
    def safe_replace_or_save(temp_source: Path, destination: Path) -> None:
        """Move a completed temporary PDF to destination safely across drives."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_source), str(destination))

    @staticmethod
    def _atomic_write_text(target: Path, content: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.replace(tmp_name, target)
        except Exception:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise
