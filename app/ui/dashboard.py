"""Home dashboard and recent files workspace with drag-and-drop support."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.file_service import FileService


class DashboardWidget(QWidget):
    """Landing dashboard with quick actions, drop zone, and recent documents."""

    open_file_dialog_requested = Signal()
    open_pdf_path_requested = Signal(str)
    navigate_requested = Signal(str)

    def __init__(self, file_service: FileService, parent=None) -> None:
        super().__init__(parent)
        self.file_service = file_service
        self.setAcceptDrops(True)
        self._build_ui()
        self.refresh_recent_files()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        hero = QFrame()
        hero.setProperty("class", "card")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)

        text_col = QVBoxLayout()
        heading = QLabel("Welcome to PDF Pro")
        heading.setStyleSheet("font-size: 20px; font-weight: 700; background: transparent;")
        sub = QLabel(
            "Local-first PDF reader, organizer, annotator, and optional Ollama assistant. "
            "Drag and drop any PDF here to open immediately."
        )
        sub.setProperty("class", "muted")
        sub.setWordWrap(True)
        text_col.addWidget(heading)
        text_col.addWidget(sub)

        btn_open_hero = QPushButton("Open PDF File...")
        btn_open_hero.setObjectName("PrimaryBtn")
        btn_open_hero.setFixedHeight(38)
        btn_open_hero.clicked.connect(self.open_file_dialog_requested.emit)

        hero_layout.addLayout(text_col, stretch=1)
        hero_layout.addSpacing(16)
        hero_layout.addWidget(btn_open_hero)
        root.addWidget(hero)

        actions_title = QLabel("Quick Workspaces")
        actions_title.setProperty("class", "section-title")
        root.addWidget(actions_title)

        grid = QGridLayout()
        grid.setSpacing(12)
        cards = [
            ("PDF Reader", "Read, zoom, search text, and inspect page thumbnails.", "reader"),
            ("Organize Pages", "Merge, split, extract, rotate, reorder, and delete pages.", "organize"),
            ("PDF Utilities", "Compress PDFs, add watermarks, edit metadata, convert images.", "tools"),
            ("Local AI Assistant", "Summarize and query open PDFs privately using Ollama.", "ai"),
        ]
        for idx, (title, desc, target_key) in enumerate(cards):
            card = QFrame()
            card.setProperty("class", "card")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(16, 14, 16, 14)
            c_layout.setSpacing(6)

            lbl_t = QLabel(title)
            lbl_t.setStyleSheet("font-weight: 700; font-size: 14px; background: transparent;")
            lbl_d = QLabel(desc)
            lbl_d.setProperty("class", "muted")
            lbl_d.setWordWrap(True)
            btn_go = QPushButton(f"Open {title}")
            btn_go.clicked.connect(lambda checked=False, k=target_key: self.navigate_requested.emit(k))

            c_layout.addWidget(lbl_t)
            c_layout.addWidget(lbl_d)
            c_layout.addStretch()
            c_layout.addWidget(btn_go)
            grid.addWidget(card, idx // 2, idx % 2)

        root.addLayout(grid)

        recent_header = QHBoxLayout()
        recent_title = QLabel("Recent Documents")
        recent_title.setProperty("class", "section-title")
        self.btn_clear_recent = QPushButton("Clear History")
        self.btn_clear_recent.clicked.connect(self._clear_history)
        recent_header.addWidget(recent_title)
        recent_header.addStretch()
        recent_header.addWidget(self.btn_clear_recent)
        root.addLayout(recent_header)

        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self._on_recent_double_clicked)
        root.addWidget(self.recent_list, stretch=1)

    def refresh_recent_files(self) -> None:
        """Reload recent PDF list from local JSON storage."""
        self.recent_list.clear()
        entries = self.file_service.get_recent_files()
        if not entries:
            placeholder = QListWidgetItem(
                "No recent PDFs yet. Click 'Open PDF' or drag a PDF onto this window."
            )
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.recent_list.addItem(placeholder)
            self.btn_clear_recent.setEnabled(False)
            return

        self.btn_clear_recent.setEnabled(True)
        for entry in entries:
            pages_txt = f"{entry.page_count} pages" if entry.page_count else "PDF"
            item = QListWidgetItem(f"{entry.name}   —   {pages_txt}   ({entry.path})")
            item.setData(Qt.ItemDataRole.UserRole, entry.path)
            self.recent_list.addItem(item)

    def _on_recent_double_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.open_pdf_path_requested.emit(str(path))

    def _clear_history(self) -> None:
        self.file_service.clear_recent_files()
        self.refresh_recent_files()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            local_path = Path(url.toLocalFile())
            if local_path.is_file() and local_path.suffix.lower() == ".pdf":
                self.open_pdf_path_requested.emit(str(local_path))
