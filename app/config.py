"""Application-wide configuration, paths, memory limits, and theme palettes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "PDF Pro"
APP_VERSION = "0.1.0-mvp"
APP_ORG = "PDFProLocal"

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
THEMES_DIR = ASSETS_DIR / "themes"
ICONS_DIR = ASSETS_DIR / "icons"

# User local app data directory (Windows: %LOCALAPPDATA%\PDFPro)
LOCAL_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".pdfpro")) / "PDFPro"
LOGS_DIR = LOCAL_DATA_DIR / "logs"
RECENT_FILES_PATH = LOCAL_DATA_DIR / "recent_files.json"
SETTINGS_PATH = LOCAL_DATA_DIR / "settings.json"

# Memory & rendering guardrails (tuned for 8 GB RAM laptops)
PIXMAP_CACHE_MAX_PAGES = 14
THUMBNAIL_CACHE_MAX_PAGES = 60
DEFAULT_ZOOM = 1.0
MIN_ZOOM = 0.25
MAX_ZOOM = 4.0
ZOOM_STEP = 0.15
RENDER_DPI_BASE = 144  # Crisp rendering on standard and 125%/150% Windows scaling
THUMBNAIL_WIDTH_PX = 140

# Local Ollama defaults (no cloud endpoints)
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_DEFAULT_MODEL = "qwen2.5:1.5b"
OLLAMA_TIMEOUT_SECONDS = 120
AI_MAX_CONTEXT_CHARS = 7500


@dataclass(frozen=True)
class ThemePalette:
    """Color tokens for PDF Pro UI themes."""

    name: str
    background: str
    panel_main: str
    panel_secondary: str
    border: str
    text_primary: str
    text_secondary: str
    accent_primary: str
    accent_secondary: str
    danger: str
    success: str
    warning: str


DARK_PALETTE = ThemePalette(
    name="dark",
    background="#080D18",
    panel_main="#0E1727",
    panel_secondary="#111D30",
    border="#21314A",
    text_primary="#EEF4FF",
    text_secondary="#8DA0BB",
    accent_primary="#4D7CFF",
    accent_secondary="#60D5E8",
    danger="#F25F5C",
    success="#2EC4B6",
    warning="#FFB703",
)

LIGHT_PALETTE = ThemePalette(
    name="light",
    background="#F3F6FB",
    panel_main="#FFFFFF",
    panel_secondary="#E8EEF7",
    border="#CBD5E1",
    text_primary="#0F172A",
    text_secondary="#475569",
    accent_primary="#2563EB",
    accent_secondary="#0891B2",
    danger="#DC2626",
    success="#059669",
    warning="#D97706",
)


def ensure_app_directories() -> None:
    """Create local runtime directories safely if they do not exist."""
    LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
