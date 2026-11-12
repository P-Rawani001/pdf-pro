"""Dynamic QSS stylesheet generator for PDF Pro Dark and Light themes."""

from __future__ import annotations

from app.config import DARK_PALETTE, LIGHT_PALETTE, ThemePalette


def get_palette(theme_name: str) -> ThemePalette:
    """Return the ThemePalette matching 'dark' or 'light'."""
    return LIGHT_PALETTE if theme_name.lower() == "light" else DARK_PALETTE


def build_stylesheet(palette: ThemePalette) -> str:
    """Generate clean, high-contrast Qt Style Sheet rules."""
    p = palette
    return f"""
    QMainWindow, QWidget {{
        background-color: {p.background};
        color: {p.text_primary};
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 13px;
    }}

    /* Left Navigation Rail */
    QFrame#Sidebar {{
        background-color: {p.panel_main};
        border-right: 1px solid {p.border};
    }}
    QLabel#AppTitle {{
        font-size: 17px;
        font-weight: 700;
        color: {p.text_primary};
        background: transparent;
    }}
    QLabel#AppBadge {{
        font-size: 11px;
        font-weight: 600;
        color: {p.accent_secondary};
        background-color: {p.panel_secondary};
        border: 1px solid {p.border};
        border-radius: 4px;
        padding: 2px 6px;
    }}
    QPushButton[class="nav-btn"] {{
        text-align: left;
        padding: 10px 14px;
        border-radius: 8px;
        border: 1px solid transparent;
        background-color: transparent;
        color: {p.text_secondary};
        font-weight: 500;
    }}
    QPushButton[class="nav-btn"]:hover {{
        background-color: {p.panel_secondary};
        color: {p.text_primary};
    }}
    QPushButton[class="nav-btn"][active="true"] {{
        background-color: {p.panel_secondary};
        color: {p.text_primary};
        border: 1px solid {p.accent_primary};
        font-weight: 600;
    }}

    /* Top Toolbar */
    QFrame#TopToolbar {{
        background-color: {p.panel_main};
        border-bottom: 1px solid {p.border};
    }}
    QPushButton {{
        background-color: {p.panel_secondary};
        color: {p.text_primary};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 6px 12px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        border-color: {p.accent_primary};
        background-color: {p.panel_main};
    }}
    QPushButton:disabled {{
        color: {p.text_secondary};
        opacity: 0.5;
    }}
    QPushButton#PrimaryBtn {{
        background-color: {p.accent_primary};
        color: #FFFFFF;
        border: 1px solid {p.accent_primary};
        font-weight: 600;
    }}
    QPushButton#PrimaryBtn:hover {{
        background-color: {p.accent_secondary};
        color: #080D18;
        border-color: {p.accent_secondary};
    }}

    /* Inputs & Search */
    QLineEdit, QSpinBox, QComboBox {{
        background-color: {p.background};
        color: {p.text_primary};
        border: 1px solid {p.border};
        border-radius: 6px;
        padding: 5px 9px;
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {p.accent_primary};
    }}

    /* Tabs */
    QTabWidget::pane {{
        border: none;
        background-color: {p.background};
    }}
    QTabBar::tab {{
        background-color: {p.panel_main};
        color: {p.text_secondary};
        border: 1px solid {p.border};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 7px 14px;
        margin-right: 3px;
    }}
    QTabBar::tab:selected {{
        background-color: {p.panel_secondary};
        color: {p.text_primary};
        border-top: 2px solid {p.accent_primary};
        font-weight: 600;
    }}

    /* Cards & Right Inspector */
    QFrame[class="card"] {{
        background-color: {p.panel_main};
        border: 1px solid {p.border};
        border-radius: 10px;
    }}
    QFrame[class="card"]:hover {{
        border-color: {p.accent_primary};
    }}
    QFrame#RightPanel {{
        background-color: {p.panel_main};
        border-left: 1px solid {p.border};
    }}
    QLabel[class="muted"] {{
        color: {p.text_secondary};
        background: transparent;
    }}
    QLabel[class="section-title"] {{
        font-size: 15px;
        font-weight: 700;
        color: {p.text_primary};
        background: transparent;
    }}

    /* Lists & Scrollbars */
    QListWidget {{
        background-color: {p.panel_main};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 6px;
    }}
    QListWidget::item:selected {{
        background-color: {p.panel_secondary};
        border: 1px solid {p.accent_primary};
        color: {p.text_primary};
    }}
    QStatusBar {{
        background-color: {p.panel_main};
        color: {p.text_secondary};
        border-top: 1px solid {p.border};
    }}
    """
