"""Top contextual toolbar for document actions, zoom, navigation, and search."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
)


class TopToolbar(QFrame):
    """Top toolbar providing core PDF controls."""

    open_requested = Signal()
    save_as_requested = Signal()
    prev_page_requested = Signal()
    next_page_requested = Signal()
    page_jump_requested = Signal(int)
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    fit_width_requested = Signal()
    fit_page_requested = Signal()
    search_requested = Signal(str)
    toggle_right_panel_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TopToolbar")
        self.setFixedHeight(52)
        self._build_ui()
        self.set_document_controls_enabled(False)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self.btn_open = QPushButton("Open PDF")
        self.btn_open.setObjectName("PrimaryBtn")
        self.btn_open.clicked.connect(self.open_requested.emit)
        layout.addWidget(self.btn_open)

        self.btn_save = QPushButton("Save Copy")
        self.btn_save.clicked.connect(self.save_as_requested.emit)
        layout.addWidget(self.btn_save)

        layout.addSpacing(8)

        self.btn_prev = QPushButton("Prev")
        self.btn_prev.clicked.connect(self.prev_page_requested.emit)
        layout.addWidget(self.btn_prev)

        self.spin_page = QSpinBox()
        self.spin_page.setMinimum(1)
        self.spin_page.setMaximum(1)
        self.spin_page.setFixedWidth(68)
        self.spin_page.valueChanged.connect(self.page_jump_requested.emit)
        layout.addWidget(self.spin_page)

        self.lbl_total_pages = QLabel("/ 0")
        self.lbl_total_pages.setProperty("class", "muted")
        layout.addWidget(self.lbl_total_pages)

        self.btn_next = QPushButton("Next")
        self.btn_next.clicked.connect(self.next_page_requested.emit)
        layout.addWidget(self.btn_next)

        layout.addSpacing(8)

        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setFixedWidth(32)
        self.btn_zoom_out.clicked.connect(self.zoom_out_requested.emit)
        layout.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setFixedWidth(48)
        layout.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedWidth(32)
        self.btn_zoom_in.clicked.connect(self.zoom_in_requested.emit)
        layout.addWidget(self.btn_zoom_in)

        self.btn_fit_width = QPushButton("Fit Width")
        self.btn_fit_width.clicked.connect(self.fit_width_requested.emit)
        layout.addWidget(self.btn_fit_width)

        self.btn_fit_page = QPushButton("Fit Page")
        self.btn_fit_page.clicked.connect(self.fit_page_requested.emit)
        layout.addWidget(self.btn_fit_page)

        layout.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Find in document...")
        self.search_input.setFixedWidth(200)
        self.search_input.returnPressed.connect(
            lambda: self.search_requested.emit(self.search_input.text())
        )
        layout.addWidget(self.search_input)

        self.btn_search = QPushButton("Find")
        self.btn_search.clicked.connect(
            lambda: self.search_requested.emit(self.search_input.text())
        )
        layout.addWidget(self.btn_search)

        self.btn_panel = QPushButton("Inspector")
        self.btn_panel.clicked.connect(self.toggle_right_panel_requested.emit)
        layout.addWidget(self.btn_panel)

    def set_document_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable PDF-specific buttons when tabs open/close."""
        for widget in (
            self.btn_save,
            self.btn_prev,
            self.spin_page,
            self.btn_next,
            self.btn_zoom_out,
            self.btn_zoom_in,
            self.btn_fit_width,
            self.btn_fit_page,
            self.search_input,
            self.btn_search,
        ):
            widget.setEnabled(enabled)

    def update_page_state(self, current_page_1based: int, total_pages: int) -> None:
        """Sync page counter without re-triggering page jump signals."""
        self.spin_page.blockSignals(True)
        self.spin_page.setMaximum(max(1, total_pages))
        self.spin_page.setValue(max(1, current_page_1based))
        self.spin_page.blockSignals(False)
        self.lbl_total_pages.setText(f"/ {total_pages}")
        self.btn_prev.setEnabled(current_page_1based > 1)
        self.btn_next.setEnabled(current_page_1based < total_pages)

    def update_zoom_label(self, zoom: float) -> None:
        """Display rounded percentage zoom."""
        self.lbl_zoom.setText(f"{int(round(zoom * 100))}%")
