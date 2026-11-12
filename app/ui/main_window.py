"""Main desktop window coordinating sidebar, toolbar, multi-tab PDF viewer, tools, and AI inspector."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, APP_VERSION, THUMBNAIL_WIDTH_PX
from app.core.annotation_manager import ANNOTATION_COLORS
from app.core.document_manager import (
    PdfOpenError,
    PdfPasswordRequiredError,
    open_pdf_session,
)
from app.core.pdf_renderer import PdfRenderer
from app.services.file_service import FileService
from app.ui.ai_panel import AiAssistantPanel
from app.ui.dashboard import DashboardWidget
from app.ui.organize_view import OrganizeWorkspaceWidget
from app.ui.pdf_viewer import PdfViewerWidget
from app.ui.sidebar import Sidebar
from app.ui.theme import build_stylesheet, get_palette
from app.ui.toolbar import TopToolbar
from app.ui.tools_view import ToolsWorkspaceWidget

logger = logging.getLogger("pdf_pro.main_window")


class MainWindow(QMainWindow):
    """Primary application shell for PDF Pro."""

    def __init__(self, file_service: FileService) -> None:
        super().__init__()
        self.file_service = file_service
        self.settings = self.file_service.load_settings()
        self.renderer = PdfRenderer()

        self.setWindowTitle(f"{APP_NAME} — Local Document Suite")
        self.resize(1380, 860)
        self.setMinimumSize(1024, 680)
        self.setAcceptDrops(True)

        self._build_ui()
        self._bind_shortcuts()
        self.apply_theme(self.settings.get("theme", "dark"))

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QHBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigation_changed.connect(self._on_navigation_changed)
        outer_layout.addWidget(self.sidebar)

        right_container = QWidget()
        center_vbox = QVBoxLayout(right_container)
        center_vbox.setContentsMargins(0, 0, 0, 0)
        center_vbox.setSpacing(0)

        self.toolbar = TopToolbar()
        self.toolbar.open_requested.connect(self.open_file_dialog)
        self.toolbar.save_as_requested.connect(self.save_copy_dialog)
        self.toolbar.prev_page_requested.connect(lambda: self._with_viewer(lambda v: v.prev_page()))
        self.toolbar.next_page_requested.connect(lambda: self._with_viewer(lambda v: v.next_page()))
        self.toolbar.page_jump_requested.connect(
            lambda p: self._with_viewer(lambda v: v.go_to_page(p))
        )
        self.toolbar.zoom_in_requested.connect(lambda: self._with_viewer(lambda v: v.zoom_in()))
        self.toolbar.zoom_out_requested.connect(lambda: self._with_viewer(lambda v: v.zoom_out()))
        self.toolbar.fit_width_requested.connect(lambda: self._with_viewer(lambda v: v.fit_width()))
        self.toolbar.fit_page_requested.connect(lambda: self._with_viewer(lambda v: v.fit_page()))
        self.toolbar.search_requested.connect(
            lambda q: self._with_viewer(lambda v: v.search(q))
        )
        self.toolbar.toggle_right_panel_requested.connect(self._toggle_right_panel)
        center_vbox.addWidget(self.toolbar)

        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(0)

        self.workspace_stack = QStackedWidget()

        # Index 0: Home / Recent Dashboard
        self.dashboard = DashboardWidget(self.file_service)
        self.dashboard.open_file_dialog_requested.connect(self.open_file_dialog)
        self.dashboard.open_pdf_path_requested.connect(self.open_pdf_file)
        self.dashboard.navigate_requested.connect(self._navigate_from_dashboard)
        self.workspace_stack.addWidget(self.dashboard)

        # Index 1: Multi-tab Document Workspace
        self.doc_tabs = QTabWidget()
        self.doc_tabs.setTabsClosable(True)
        self.doc_tabs.setMovable(True)
        self.doc_tabs.tabCloseRequested.connect(self._close_tab)
        self.doc_tabs.currentChanged.connect(self._on_tab_changed)
        self.workspace_stack.addWidget(self.doc_tabs)

        # Index 2: Organize Pages Workspace
        self.organize_view = OrganizeWorkspaceWidget(self.file_service, self.renderer)
        self.organize_view.open_pdf_requested.connect(self.open_pdf_file)
        self.organize_view.status_message.connect(lambda msg: self.status_bar.showMessage(msg, 5000))
        self.workspace_stack.addWidget(self.organize_view)

        # Index 3: PDF Utilities Workspace
        self.tools_view = ToolsWorkspaceWidget(self.file_service)
        self.tools_view.open_pdf_requested.connect(self.open_pdf_file)
        self.tools_view.status_message.connect(lambda msg: self.status_bar.showMessage(msg, 5000))
        self.workspace_stack.addWidget(self.tools_view)

        # Index 4: Settings View
        self.settings_view = self._build_settings_view()
        self.workspace_stack.addWidget(self.settings_view)

        body_row.addWidget(self.workspace_stack, stretch=1)

        # Right Inspector Panel (0: Thumbnails, 1: Annotations, 2: Local AI Assistant)
        self.right_panel = QFrame()
        self.right_panel.setObjectName("RightPanel")
        self.right_panel.setFixedWidth(300)
        rp_layout = QVBoxLayout(self.right_panel)
        rp_layout.setContentsMargins(12, 12, 12, 12)
        rp_layout.setSpacing(10)

        self.right_panel_title = QLabel("Page Thumbnails")
        self.right_panel_title.setProperty("class", "section-title")
        rp_layout.addWidget(self.right_panel_title)

        self.right_stack = QStackedWidget()

        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setIconSize(QSize(THUMBNAIL_WIDTH_PX, 190))
        self.thumbnail_list.setSpacing(6)
        self.thumbnail_list.itemClicked.connect(self._on_thumbnail_clicked)
        self.right_stack.addWidget(self.thumbnail_list)

        self.right_stack.addWidget(self._build_annotation_panel())

        self.ai_panel = AiAssistantPanel(self.file_service)
        self.ai_panel.status_message.connect(lambda msg: self.status_bar.showMessage(msg, 5000))
        self.right_stack.addWidget(self.ai_panel)

        rp_layout.addWidget(self.right_stack, stretch=1)

        self.doc_info_label = QLabel("No document open")
        self.doc_info_label.setProperty("class", "muted")
        self.doc_info_label.setWordWrap(True)
        rp_layout.addWidget(self.doc_info_label)

        self.right_panel.setVisible(bool(self.settings.get("right_panel_visible", True)))
        body_row.addWidget(self.right_panel)

        center_vbox.addLayout(body_row, stretch=1)
        outer_layout.addWidget(right_container, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready  •  Offline Local Mode")

    def _build_annotation_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        hint = QLabel(
            "Choose a tool below, then drag across the PDF page. "
            "Annotations are non-destructive markups—use Save Copy (Ctrl+S) to export."
        )
        hint.setProperty("class", "muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color:"))
        self.annot_color_combo = QComboBox()
        self.annot_color_combo.addItems(list(ANNOTATION_COLORS.keys()))
        self.annot_color_combo.currentTextChanged.connect(self._apply_selected_annot_tool)
        color_row.addWidget(self.annot_color_combo, stretch=1)
        layout.addLayout(color_row)

        self.annot_tool_combo = QComboBox()
        self._annot_modes = [
            ("select", "Select & Copy Text (Default)"),
            ("highlight", "Highlight Region"),
            ("underline", "Underline Text"),
            ("strikeout", "Strike-through Text"),
            ("sticky_note", "Sticky Note Comment"),
            ("freetext", "Free Text Box"),
            ("rectangle", "Rectangle Box"),
        ]
        for _, label in self._annot_modes:
            self.annot_tool_combo.addItem(label)
        self.annot_tool_combo.currentIndexChanged.connect(self._apply_selected_annot_tool)
        layout.addWidget(self.annot_tool_combo)

        btn_undo_annot = QPushButton("Undo Last Annotation on Page")
        btn_undo_annot.clicked.connect(
            lambda: self._with_viewer(lambda v: v.undo_last_annotation())
        )
        layout.addWidget(btn_undo_annot)

        btn_save_annot = QPushButton("Save Annotated PDF As...")
        btn_save_annot.setObjectName("PrimaryBtn")
        btn_save_annot.clicked.connect(self.save_copy_dialog)
        layout.addWidget(btn_save_annot)

        layout.addStretch()
        return panel

    def _apply_selected_annot_tool(self) -> None:
        idx = self.annot_tool_combo.currentIndex()
        mode = self._annot_modes[idx][0]
        color = self.annot_color_combo.currentText()
        self._with_viewer(lambda v: v.set_interaction_mode(mode, color))
        self.status_bar.showMessage(f"Tool active: {self._annot_modes[idx][1]} ({color})", 3000)

    def _build_settings_view(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Application Settings")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(title)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 18, 20, 18)
        c_layout.setSpacing(12)

        row = QHBoxLayout()
        lbl = QLabel("Interface Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Theme (Default)", "Light Theme"])
        current_theme = self.settings.get("theme", "dark")
        self.theme_combo.setCurrentIndex(1 if current_theme == "light" else 0)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        row.addWidget(lbl)
        row.addWidget(self.theme_combo)
        row.addStretch()
        c_layout.addLayout(row)

        privacy_note = QLabel(
            f"{APP_NAME} v{APP_VERSION} processes all PDFs locally on Windows. "
            "Optional AI features connect exclusively to local Ollama (http://127.0.0.1:11434)."
        )
        privacy_note.setProperty("class", "muted")
        privacy_note.setWordWrap(True)
        c_layout.addWidget(privacy_note)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self.open_file_dialog)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_copy_dialog)
        QShortcut(QKeySequence("Ctrl+W"), self, activated=self._close_current_tab)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)
        QShortcut(QKeySequence("Ctrl++"), self, activated=lambda: self._with_viewer(lambda v: v.zoom_in()))
        QShortcut(QKeySequence("Ctrl+="), self, activated=lambda: self._with_viewer(lambda v: v.zoom_in()))
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self._with_viewer(lambda v: v.zoom_out()))
        QShortcut(QKeySequence("Ctrl+0"), self, activated=lambda: self._with_viewer(lambda v: v.reset_zoom()))
        QShortcut(QKeySequence("Ctrl+C"), self, activated=lambda: self._with_viewer(lambda v: v.copy_selected_or_page_text()))

    def _focus_search(self) -> None:
        if self.toolbar.search_input.isEnabled():
            self.toolbar.search_input.setFocus()
            self.toolbar.search_input.selectAll()

    def _current_viewer(self) -> PdfViewerWidget | None:
        widget = self.doc_tabs.currentWidget()
        return widget if isinstance(widget, PdfViewerWidget) else None

    def _with_viewer(self, fn) -> None:
        viewer = self._current_viewer()
        if viewer is not None:
            fn(viewer)

    def apply_theme(self, theme_name: str) -> None:
        palette = get_palette(theme_name)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(palette))

    def _on_theme_changed(self, index: int) -> None:
        chosen = "light" if index == 1 else "dark"
        self.settings["theme"] = chosen
        self.file_service.save_settings(self.settings)
        self.apply_theme(chosen)
        self.status_bar.showMessage(f"Switched to {chosen.title()} theme", 3000)

    def _navigate_from_dashboard(self, key: str) -> None:
        self.sidebar.select_item(key, emit_signal=True)

    def _on_navigation_changed(self, key: str) -> None:
        viewer = self._current_viewer()
        if key in ("home", "recent"):
            self.dashboard.refresh_recent_files()
            self.workspace_stack.setCurrentWidget(self.dashboard)
            self.right_stack.setCurrentIndex(0)
        elif key == "organize":
            self.organize_view.bind_session(viewer.session if viewer else None)
            self.workspace_stack.setCurrentWidget(self.organize_view)
            self.right_stack.setCurrentIndex(0)
        elif key == "tools":
            self.tools_view.bind_session(viewer.session if viewer else None)
            self.workspace_stack.setCurrentWidget(self.tools_view)
            self.right_stack.setCurrentIndex(0)
        elif key == "settings":
            self.workspace_stack.setCurrentWidget(self.settings_view)
            self.right_stack.setCurrentIndex(0)
        elif key == "editor":
            self.workspace_stack.setCurrentWidget(self.doc_tabs)
            self.right_panel.setVisible(True)
            self.right_stack.setCurrentIndex(1)
            if self.annot_tool_combo.currentIndex() == 0:
                self.annot_tool_combo.setCurrentIndex(1)
            self._apply_selected_annot_tool()
        elif key == "ai":
            self.workspace_stack.setCurrentWidget(self.doc_tabs)
            self.right_panel.setVisible(True)
            self.right_stack.setCurrentIndex(2)
            self.ai_panel.bind_session(viewer.session if viewer else None)
            self._with_viewer(lambda v: v.set_interaction_mode("select"))
        else:
            if self.doc_tabs.count() == 0:
                self.status_bar.showMessage(
                    f"Switched to {key.title()} — open a PDF to begin.", 4000
                )
            self.workspace_stack.setCurrentWidget(self.doc_tabs)
            self.right_stack.setCurrentIndex(0)
            self._with_viewer(lambda v: v.set_interaction_mode("select"))

        panel_titles = {
            "reader": "Page Thumbnails",
            "editor": "Annotation Tools",
            "organize": "Page Operations",
            "tools": "PDF Utilities",
            "ai": "Local Ollama Assistant",
        }
        self.right_panel_title.setText(panel_titles.get(key, "Page Thumbnails"))

    def _toggle_right_panel(self) -> None:
        visible = not self.right_panel.isVisible()
        self.right_panel.setVisible(visible)
        self.settings["right_panel_visible"] = visible
        self.file_service.save_settings(self.settings)

    def open_file_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open PDF Document(s)",
            str(Path.home()),
            "PDF Documents (*.pdf);;All Files (*.*)",
        )
        for p in paths:
            self.open_pdf_file(p)

    def open_pdf_file(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            QMessageBox.warning(self, "File Not Found", f"Cannot locate:\n{file_path}")
            return
        if path.suffix.lower() != ".pdf":
            QMessageBox.warning(self, "Unsupported File", "Please select a valid .pdf file.")
            return

        for i in range(self.doc_tabs.count()):
            w = self.doc_tabs.widget(i)
            if isinstance(w, PdfViewerWidget) and w.session.file_path == path.resolve():
                self.doc_tabs.setCurrentIndex(i)
                self.workspace_stack.setCurrentWidget(self.doc_tabs)
                return

        password: str | None = None
        while True:
            try:
                session = open_pdf_session(path, password=password)
                break
            except PdfPasswordRequiredError:
                pwd, ok = QInputDialog.getText(
                    self,
                    "Encrypted PDF",
                    f"Enter password for {path.name}:",
                    QLineEdit.EchoMode.Password,
                )
                if not ok:
                    return
                password = pwd
            except PdfOpenError as exc:
                QMessageBox.critical(self, "Cannot Open PDF", str(exc))
                return

        viewer = PdfViewerWidget(session=session, renderer=self.renderer)
        viewer.page_changed.connect(self._on_viewer_page_changed)
        viewer.zoom_changed.connect(self.toolbar.update_zoom_label)
        viewer.status_message.connect(lambda msg: self.status_bar.showMessage(msg, 5000))
        viewer.document_modified.connect(lambda: self._populate_inspector_for_viewer(viewer))
        viewer.text_selection_changed.connect(self.ai_panel.set_selected_text)

        idx = self.doc_tabs.addTab(viewer, session.name)
        self.doc_tabs.setCurrentIndex(idx)
        self.toolbar.set_document_controls_enabled(True)
        self.sidebar.select_item("reader", emit_signal=False)
        self.workspace_stack.setCurrentWidget(self.doc_tabs)
        self.right_stack.setCurrentIndex(0)

        self.file_service.add_recent_file(path, page_count=session.page_count)
        self.dashboard.refresh_recent_files()
        self._populate_inspector_for_viewer(viewer)
        self.organize_view.bind_session(session)
        self.tools_view.bind_session(session)
        self.ai_panel.bind_session(session)
        self.status_bar.showMessage(
            f"Opened {session.name} ({session.page_count} pages)"
        )

    def _on_tab_changed(self, index: int) -> None:
        viewer = self._current_viewer()
        if viewer is None:
            self.toolbar.set_document_controls_enabled(False)
            self.thumbnail_list.clear()
            self.doc_info_label.setText("No document open")
            self.organize_view.bind_session(None)
            self.tools_view.bind_session(None)
            self.ai_panel.bind_session(None)
            return

        self.toolbar.set_document_controls_enabled(True)
        self.toolbar.update_page_state(
            viewer.session.current_page + 1, viewer.session.page_count
        )
        self.toolbar.update_zoom_label(viewer.session.zoom)
        self._populate_inspector_for_viewer(viewer)
        self.organize_view.bind_session(viewer.session)
        self.tools_view.bind_session(viewer.session)
        self.ai_panel.bind_session(viewer.session)

    def _on_viewer_page_changed(self, current_1based: int, total: int) -> None:
        self.toolbar.update_page_state(current_1based, total)
        if 0 <= current_1based - 1 < self.thumbnail_list.count():
            self.thumbnail_list.setCurrentRow(current_1based - 1)

    def _populate_inspector_for_viewer(self, viewer: PdfViewerWidget) -> None:
        self.thumbnail_list.clear()
        total = viewer.session.page_count
        preview_limit = min(total, 60)
        for page_idx in range(preview_limit):
            thumb = self.renderer.render_thumbnail(viewer.session.doc, page_idx)
            item = QListWidgetItem(QIcon(thumb), f"Page {page_idx + 1}")
            item.setData(Qt.ItemDataRole.UserRole, page_idx + 1)
            self.thumbnail_list.addItem(item)

        if total > preview_limit:
            note = QListWidgetItem(f"... {total - preview_limit} more pages (use page box)")
            note.setFlags(Qt.ItemFlag.NoItemFlags)
            self.thumbnail_list.addItem(note)

        if 0 <= viewer.session.current_page < self.thumbnail_list.count():
            self.thumbnail_list.setCurrentRow(viewer.session.current_page)

        meta = viewer.session.get_metadata()
        title_str = meta["Title"] or viewer.session.name
        author_str = meta["Author"] or "Unknown"
        self.doc_info_label.setText(
            f"Title: {title_str}\nAuthor: {author_str}\nPages: {total}"
        )

    def _on_thumbnail_clicked(self, item: QListWidgetItem) -> None:
        page_1based = item.data(Qt.ItemDataRole.UserRole)
        if page_1based:
            self._with_viewer(lambda v: v.go_to_page(int(page_1based)))

    def save_copy_dialog(self) -> None:
        viewer = self._current_viewer()
        if viewer is None:
            return
        suggested = viewer.session.file_path.with_name(
            f"{viewer.session.file_path.stem}_copy.pdf"
        )
        dest_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save Copy of PDF",
            str(suggested),
            "PDF Documents (*.pdf)",
        )
        if not dest_str:
            return
        dest = Path(dest_str)
        if dest.resolve() == viewer.session.file_path:
            reply = QMessageBox.question(
                self,
                "Overwrite Original?",
                "You selected the original source file. Overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            viewer.session.save_copy(dest, self.file_service)
            self.status_bar.showMessage(f"Saved copy to {dest.name}", 5000)
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", f"Could not save PDF:\n{exc}")

    def _close_tab(self, index: int) -> None:
        widget = self.doc_tabs.widget(index)
        self.doc_tabs.removeTab(index)
        if isinstance(widget, PdfViewerWidget):
            self.renderer.invalidate_document(widget.session.doc)
            widget.session.close()
        if widget is not None:
            widget.deleteLater()
        if self.doc_tabs.count() == 0:
            self.toolbar.set_document_controls_enabled(False)
            self.organize_view.bind_session(None)
            self.tools_view.bind_session(None)
            self.ai_panel.bind_session(None)
            self.sidebar.select_item("home", emit_signal=True)

    def _close_current_tab(self) -> None:
        if self.doc_tabs.count() > 0:
            self._close_tab(self.doc_tabs.currentIndex())

    def closeEvent(self, event) -> None:
        while self.doc_tabs.count() > 0:
            self._close_tab(0)
        super().closeEvent(event)

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
                self.open_pdf_file(str(local_path))
