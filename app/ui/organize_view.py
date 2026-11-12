"""Organize Pages workspace: Reorder, Rotate, Delete, Extract, Merge, and Split PDFs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap, QTransform
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.document_manager import PdfDocumentSession
from app.core.page_manager import PageOperationError, PagePlan
from app.core.pdf_renderer import PdfRenderer
from app.operations.merge import PdfMergeError, merge_pdfs
from app.operations.split import (
    PdfSplitError,
    extract_pages_to_pdf,
    parse_page_ranges,
    split_into_single_pages,
)
from app.services.file_service import FileService


class OrganizeWorkspaceWidget(QWidget):
    """Complete Page Organization workspace (Arrange, Merge, Split)."""

    open_pdf_requested = Signal(str)
    status_message = Signal(str)

    THUMBNAIL_RENDER_CAP = 60

    def __init__(
        self,
        file_service: FileService,
        renderer: PdfRenderer,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.file_service = file_service
        self.renderer = renderer
        self._session: PdfDocumentSession | None = None
        self._plan: PagePlan | None = None
        self._placeholder_icon = self._make_placeholder_icon()
        self._build_ui()

    @staticmethod
    def _make_placeholder_icon() -> QIcon:
        pix = QPixmap(110, 150)
        pix.fill(QColor("#111D30"))
        return QIcon(pix)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        header = QLabel("Organize Pages — Arrange, Merge & Split")
        header.setStyleSheet("font-size: 19px; font-weight: 700;")
        root.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_arrange_tab(), "1. Reorder / Rotate / Delete / Extract")
        self.tabs.addTab(self._build_merge_tab(), "2. Merge Multiple PDFs")
        self.tabs.addTab(self._build_split_tab(), "3. Split PDF")
        root.addWidget(self.tabs, stretch=1)

    def _build_arrange_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        self.arrange_doc_label = QLabel(
            "No active PDF open. Open a PDF first to reorder, rotate, delete, or extract pages."
        )
        self.arrange_doc_label.setProperty("class", "muted")
        layout.addWidget(self.arrange_doc_label)

        bar = QHBoxLayout()
        bar.setSpacing(8)

        self.btn_rot_left = QPushButton("Rotate -90°")
        self.btn_rot_left.clicked.connect(lambda: self._rotate_selected(-90))
        bar.addWidget(self.btn_rot_left)

        self.btn_rot_right = QPushButton("Rotate +90°")
        self.btn_rot_right.clicked.connect(lambda: self._rotate_selected(90))
        bar.addWidget(self.btn_rot_right)

        self.btn_move_up = QPushButton("Move Earlier")
        self.btn_move_up.clicked.connect(self._move_selected_up)
        bar.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("Move Later")
        self.btn_move_down.clicked.connect(self._move_selected_down)
        bar.addWidget(self.btn_move_down)

        self.btn_delete_pages = QPushButton("Delete Selected")
        self.btn_delete_pages.clicked.connect(self._delete_selected)
        bar.addWidget(self.btn_delete_pages)

        self.btn_extract_pages = QPushButton("Extract Selected...")
        self.btn_extract_pages.clicked.connect(self._extract_selected)
        bar.addWidget(self.btn_extract_pages)

        self.btn_reset_plan = QPushButton("Reset")
        self.btn_reset_plan.clicked.connect(self._reset_plan)
        bar.addWidget(self.btn_reset_plan)

        bar.addStretch()

        self.btn_save_organized = QPushButton("Save Organized PDF As...")
        self.btn_save_organized.setObjectName("PrimaryBtn")
        self.btn_save_organized.clicked.connect(self._save_organized_pdf)
        bar.addWidget(self.btn_save_organized)

        layout.addLayout(bar)

        self.page_grid = QListWidget()
        self.page_grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.page_grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.page_grid.setMovement(QListWidget.Movement.Static)
        self.page_grid.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.page_grid.setIconSize(QSize(130, 175))
        self.page_grid.setGridSize(QSize(165, 220))
        self.page_grid.setSpacing(10)
        layout.addWidget(self.page_grid, stretch=1)

        self._set_arrange_controls_enabled(False)
        return tab

    def _set_arrange_controls_enabled(self, enabled: bool) -> None:
        for btn in (
            self.btn_rot_left,
            self.btn_rot_right,
            self.btn_move_up,
            self.btn_move_down,
            self.btn_delete_pages,
            self.btn_extract_pages,
            self.btn_reset_plan,
            self.btn_save_organized,
        ):
            btn.setEnabled(enabled)

    def bind_session(self, session: PdfDocumentSession | None) -> None:
        self._session = session
        if session is None:
            self._plan = None
            self.page_grid.clear()
            self.arrange_doc_label.setText(
                "No active PDF open. Open a PDF first to organize its pages."
            )
            self._set_arrange_controls_enabled(False)
            self.split_source_edit.clear()
            return

        self._plan = PagePlan(session.page_count)
        cap_note = (
            f" (thumbnails rendered for first {self.THUMBNAIL_RENDER_CAP} pages to save RAM)"
            if session.page_count > self.THUMBNAIL_RENDER_CAP
            else ""
        )
        self.arrange_doc_label.setText(
            f"Active Document: {session.name} ({session.page_count} pages){cap_note}"
        )
        self._set_arrange_controls_enabled(True)
        self.split_source_edit.setText(str(session.file_path))
        self._refresh_page_grid()

    def _refresh_page_grid(self, select_rows: list[int] | None = None) -> None:
        self.page_grid.clear()
        if self._session is None or self._plan is None:
            return

        for pos, item in enumerate(self._plan.items):
            if pos < self.THUMBNAIL_RENDER_CAP:
                pix = self.renderer.render_thumbnail(
                    self._session.doc, item.source_page_index, width_px=130
                )
                if item.rotation_delta:
                    transform = QTransform().rotate(item.rotation_delta)
                    pix = pix.transformed(transform, Qt.TransformationMode.SmoothTransformation)
                icon = QIcon(pix)
            else:
                icon = self._placeholder_icon

            rot_tag = f" ({item.rotation_delta}°)" if item.rotation_delta else ""
            label = f"Pos {pos + 1}  [Orig p.{item.source_page_index + 1}]{rot_tag}"
            self.page_grid.addItem(QListWidgetItem(icon, label))

        if select_rows:
            for r in select_rows:
                if 0 <= r < self.page_grid.count():
                    self.page_grid.item(r).setSelected(True)

    def _selected_positions(self) -> list[int]:
        return sorted(idx.row() for idx in self.page_grid.selectedIndexes())

    def _rotate_selected(self, delta: int) -> None:
        if self._plan is None:
            return
        rows = self._selected_positions()
        if not rows:
            QMessageBox.information(self, "Select Pages", "Select one or more pages first.")
            return
        self._plan.rotate_positions(rows, delta)
        self._refresh_page_grid(select_rows=rows)

    def _move_selected_up(self) -> None:
        if self._plan is None:
            return
        rows = self._selected_positions()
        if len(rows) != 1:
            QMessageBox.information(self, "Select Single Page", "Select exactly one page to reorder.")
            return
        new_pos = self._plan.move_up(rows[0])
        self._refresh_page_grid(select_rows=[new_pos])

    def _move_selected_down(self) -> None:
        if self._plan is None:
            return
        rows = self._selected_positions()
        if len(rows) != 1:
            QMessageBox.information(self, "Select Single Page", "Select exactly one page to reorder.")
            return
        new_pos = self._plan.move_down(rows[0])
        self._refresh_page_grid(select_rows=[new_pos])

    def _delete_selected(self) -> None:
        if self._plan is None:
            return
        rows = self._selected_positions()
        if not rows:
            QMessageBox.information(self, "Select Pages", "Select one or more pages to delete.")
            return
        reply = QMessageBox.question(
            self,
            "Confirm Page Removal",
            f"Remove {len(rows)} selected page(s) from the output plan?\n"
            "(Your original source file on disk will NOT be modified.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self._plan.delete_positions(rows)
            self._refresh_page_grid()
            self.status_message.emit(f"Removed {len(rows)} page(s) from output plan.")
        except PageOperationError as exc:
            QMessageBox.warning(self, "Cannot Delete", str(exc))

    def _reset_plan(self) -> None:
        if self._session is None or self._plan is None:
            return
        self._plan.reset(self._session.page_count)
        self._refresh_page_grid()
        self.status_message.emit("Reset page order and rotations to original.")

    def _extract_selected(self) -> None:
        if self._session is None or self._plan is None:
            return
        rows = self._selected_positions()
        if not rows:
            QMessageBox.information(self, "Select Pages", "Select one or more pages to extract.")
            return
        suggested = self._session.file_path.with_name(
            f"{self._session.file_path.stem}_extracted.pdf"
        )
        dest_str, _ = QFileDialog.getSaveFileName(
            self, "Save Extracted Pages As", str(suggested), "PDF Documents (*.pdf)"
        )
        if not dest_str:
            return
        dest = Path(dest_str)
        if dest.resolve() == self._session.file_path:
            QMessageBox.warning(
                self, "Choose New File", "Please choose a new filename instead of overwriting the open file."
            )
            return
        try:
            saved = self._plan.build_output_pdf(
                self._session.doc, dest, self.file_service, selected_positions=rows
            )
            self.status_message.emit(f"Extracted {len(rows)} page(s) to {saved.name}")
            if QMessageBox.question(
                self, "Open Extracted PDF?", f"Saved to:\n{saved}\n\nOpen it in a new tab?"
            ) == QMessageBox.StandardButton.Yes:
                self.open_pdf_requested.emit(str(saved))
        except PageOperationError as exc:
            QMessageBox.critical(self, "Extraction Failed", str(exc))

    def _save_organized_pdf(self) -> None:
        if self._session is None or self._plan is None:
            return
        suggested = self._session.file_path.with_name(
            f"{self._session.file_path.stem}_organized.pdf"
        )
        dest_str, _ = QFileDialog.getSaveFileName(
            self, "Save Organized PDF As", str(suggested), "PDF Documents (*.pdf)"
        )
        if not dest_str:
            return
        dest = Path(dest_str)
        if dest.resolve() == self._session.file_path:
            QMessageBox.warning(
                self, "Choose New File", "Please save to a new filename to preserve the original document."
            )
            return
        try:
            saved = self._plan.build_output_pdf(
                self._session.doc, dest, self.file_service
            )
            self.status_message.emit(f"Saved organized PDF to {saved.name}")
            if QMessageBox.question(
                self, "Open Organized PDF?", f"Saved to:\n{saved}\n\nOpen it in a new tab?"
            ) == QMessageBox.StandardButton.Yes:
                self.open_pdf_requested.emit(str(saved))
        except PageOperationError as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))

    def _build_merge_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)

        hint = QLabel("Add two or more PDF files, arrange their order, and merge into a new PDF.")
        hint.setProperty("class", "muted")
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Add PDFs...")
        btn_add.clicked.connect(self._merge_add_files)
        btn_up = QPushButton("Move Up")
        btn_up.clicked.connect(self._merge_move_up)
        btn_down = QPushButton("Move Down")
        btn_down.clicked.connect(self._merge_move_down)
        btn_rem = QPushButton("Remove")
        btn_rem.clicked.connect(self._merge_remove_selected)
        btn_clear = QPushButton("Clear List")
        btn_clear.clicked.connect(lambda: self.merge_list.clear())

        btn_merge_go = QPushButton("Merge PDFs...")
        btn_merge_go.setObjectName("PrimaryBtn")
        btn_merge_go.clicked.connect(self._execute_merge)

        for b in (btn_add, btn_up, btn_down, btn_rem, btn_clear):
            btn_row.addWidget(b)
        btn_row.addStretch()
        btn_row.addWidget(btn_merge_go)
        layout.addLayout(btn_row)

        self.merge_list = QListWidget()
        layout.addWidget(self.merge_list, stretch=1)
        return tab

    def _merge_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PDFs to Merge", str(Path.home()), "PDF Documents (*.pdf)"
        )
        for p in paths:
            item = QListWidgetItem(p)
            item.setData(Qt.ItemDataRole.UserRole, p)
            self.merge_list.addItem(item)

    def _merge_move_up(self) -> None:
        row = self.merge_list.currentRow()
        if row > 0:
            item = self.merge_list.takeItem(row)
            self.merge_list.insertItem(row - 1, item)
            self.merge_list.setCurrentRow(row - 1)

    def _merge_move_down(self) -> None:
        row = self.merge_list.currentRow()
        if 0 <= row < self.merge_list.count() - 1:
            item = self.merge_list.takeItem(row)
            self.merge_list.insertItem(row + 1, item)
            self.merge_list.setCurrentRow(row + 1)

    def _merge_remove_selected(self) -> None:
        row = self.merge_list.currentRow()
        if row >= 0:
            self.merge_list.takeItem(row)

    def _execute_merge(self) -> None:
        paths = [
            self.merge_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.merge_list.count())
        ]
        if len(paths) < 2:
            QMessageBox.warning(self, "Merge PDFs", "Add at least two PDF files to merge.")
            return
        suggested = Path(paths[0]).with_name("merged_document.pdf")
        dest_str, _ = QFileDialog.getSaveFileName(
            self, "Save Merged PDF As", str(suggested), "PDF Documents (*.pdf)"
        )
        if not dest_str:
            return
        try:
            saved = merge_pdfs(paths, dest_str, self.file_service)
            self.status_message.emit(f"Merged {len(paths)} PDFs into {saved.name}")
            if QMessageBox.question(
                self, "Merge Complete", f"Saved merged PDF to:\n{saved}\n\nOpen it now?"
            ) == QMessageBox.StandardButton.Yes:
                self.open_pdf_requested.emit(str(saved))
        except PdfMergeError as exc:
            QMessageBox.critical(self, "Merge Failed", str(exc))

    def _build_split_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(12)

        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Source PDF:"))
        self.split_source_edit = QLineEdit()
        self.split_source_edit.setPlaceholderText("Choose a PDF file to split...")
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_split_source)
        src_row.addWidget(self.split_source_edit, stretch=1)
        src_row.addWidget(btn_browse)
        c_layout.addLayout(src_row)

        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("Extract Page Range:"))
        self.split_range_edit = QLineEdit()
        self.split_range_edit.setPlaceholderText("e.g., 1-3, 5, 7-9")
        btn_extract_range = QPushButton("Extract Range to New PDF...")
        btn_extract_range.setObjectName("PrimaryBtn")
        btn_extract_range.clicked.connect(self._execute_range_split)
        range_row.addWidget(self.split_range_edit, stretch=1)
        range_row.addWidget(btn_extract_range)
        c_layout.addLayout(range_row)

        all_row = QHBoxLayout()
        lbl_all = QLabel("Or split every page into separate 1-page PDF files:")
        lbl_all.setProperty("class", "muted")
        btn_split_all = QPushButton("Split All Pages to Folder...")
        btn_split_all.clicked.connect(self._execute_full_split)
        all_row.addWidget(lbl_all, stretch=1)
        all_row.addWidget(btn_split_all)
        c_layout.addLayout(all_row)

        layout.addWidget(card)
        layout.addStretch()
        return tab

    def _browse_split_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Source PDF", str(Path.home()), "PDF Documents (*.pdf)"
        )
        if path:
            self.split_source_edit.setText(path)

    def _execute_range_split(self) -> None:
        src_str = self.split_source_edit.text().strip()
        if not src_str:
            QMessageBox.warning(self, "Split PDF", "Choose a source PDF first.")
            return
        src = Path(src_str)
        if not src.exists():
            QMessageBox.warning(self, "File Not Found", f"Cannot find:\n{src}")
            return
        try:
            from pypdf import PdfReader

            total = len(PdfReader(str(src)).pages)
            indices = parse_page_ranges(self.split_range_edit.text(), total)
            suggested = src.with_name(f"{src.stem}_pages.pdf")
            dest_str, _ = QFileDialog.getSaveFileName(
                self, "Save Extracted Range As", str(suggested), "PDF Documents (*.pdf)"
            )
            if not dest_str:
                return
            saved = extract_pages_to_pdf(src, indices, dest_str, self.file_service)
            self.status_message.emit(f"Extracted {len(indices)} pages to {saved.name}")
            if QMessageBox.question(
                self, "Extraction Complete", f"Saved to:\n{saved}\n\nOpen it now?"
            ) == QMessageBox.StandardButton.Yes:
                self.open_pdf_requested.emit(str(saved))
        except (PdfSplitError, Exception) as exc:
            QMessageBox.critical(self, "Split Failed", str(exc))

    def _execute_full_split(self) -> None:
        src_str = self.split_source_edit.text().strip()
        if not src_str:
            QMessageBox.warning(self, "Split PDF", "Choose a source PDF first.")
            return
        src = Path(src_str)
        if not src.exists():
            QMessageBox.warning(self, "File Not Found", f"Cannot find:\n{src}")
            return
        out_dir = QFileDialog.getExistingDirectory(
            self, "Choose Destination Folder for Split Pages", str(src.parent)
        )
        if not out_dir:
            return
        try:
            files = split_into_single_pages(src, out_dir, self.file_service)
            self.status_message.emit(f"Split into {len(files)} individual PDFs.")
            QMessageBox.information(
                self,
                "Split Complete",
                f"Created {len(files)} single-page PDFs in:\n{out_dir}",
            )
        except PdfSplitError as exc:
            QMessageBox.critical(self, "Split Failed", str(exc))
