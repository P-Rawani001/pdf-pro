"""Left navigation rail for switching PDF Pro workspaces."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QVBoxLayout,
)

from app.config import APP_NAME, APP_VERSION


NAV_ITEMS: list[tuple[str, str]] = [
    ("home", "Home"),
    ("recent", "Recent Files"),
    ("reader", "PDF Reader"),
    ("editor", "PDF Editor"),
    ("organize", "Organize Pages"),
    ("tools", "PDF Tools"),
    ("ai", "AI Assistant"),
    ("settings", "Settings"),
]


class Sidebar(QFrame):
    """Primary left navigation sidebar."""

    navigation_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(215)
        self._buttons: dict[str, QPushButton] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        badge = QLabel("LOCAL")
        badge.setObjectName("AppBadge")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(badge)
        layout.addLayout(header)

        subtitle = QLabel("Offline Document Suite")
        subtitle.setProperty("class", "muted")
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        for key, label in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setProperty("class", "nav-btn")
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda checked=False, k=key: self.select_item(k))
            layout.addWidget(btn)
            self._buttons[key] = btn

        layout.addItem(
            QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )

        ver_label = QLabel(f"v{APP_VERSION}  •  100% Local")
        ver_label.setProperty("class", "muted")
        layout.addWidget(ver_label)

        self.select_item("home", emit_signal=False)

    def select_item(self, key: str, emit_signal: bool = True) -> None:
        """Highlight the active navigation button and emit navigation event."""
        for item_key, btn in self._buttons.items():
            is_active = item_key == key
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if emit_signal:
            self.navigation_changed.emit(key)
