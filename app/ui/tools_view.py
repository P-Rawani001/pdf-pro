"""PDF Utilities workspace: Compress, Watermark, Metadata Editor, and Images <-> PDF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.document_manager import PdfDocumentSession
from app.core.metadata_manager import (
    PdfMetadataError,
    read_pdf_metadata,
    write_pdf_metadata,
)
from app.operations.compress import PdfCompressError, compress_pdf
from app.operations.convert import PdfConvertError, images_to_pdf, pdf_to_images
from app.operations.watermark import COLOR_PRESETS, PdfWatermarkError, add_text_watermark
from app.services.file_service import FileService


def _format_bytes(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


class ToolsWorkspaceWidget(QWidget):
    """Complete PDF Utilities workspace."""

    open_pdf_requested = Signal(str)
    status_message = Signal(str)

    def __init__(self, file_service: FileService, parent=None) -> None:
        super().__init__(parent)
        self.file_service = file_service
        self._session: PdfDocumentSession | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        header = QLabel("PDF Utilities — Compress, Watermark, Metadata & Convert")
        header.setStyleSheet("font-size: 19px; font-weight: 700;")
        root.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_compress_tab(), "1. Compress PDF")
        self.tabs.addTab(self._build_watermark_tab(), "2. Text Watermark")
        self.tabs.addTab(self._build_metadata_tab(), "3. Metadata Viewer / Editor")
        self.tabs.addTab(self._build_convert_tab(), "4. Images <-> PDF")
        root.addWidget(self.tabs, stretch=1)

    def bind_session(self, session: PdfDocumentSession | None) -> None:
        """Auto-fill source paths and metadata from the currently open PDF."""
        self._session = session
        if session is None:
            return
        path_str = str(session.file_path)
        self.comp_src_edit.setText(path_str)
        self.wm_src_edit.setText(path_str)
        self.meta_src_edit.setText(path_str)
        self.p2i_src_edit.setText(path_str)
        self._load_metadata_fields(session.file_path)

    # --- TAB 1: COMPRESS ---
    def _build_compress_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(12)

        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Source PDF:"))
        self.comp_src_edit = QLineEdit()
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(lambda: self._pick_pdf(self.comp_src_edit))
        src_row.addWidget(self.comp_src_edit, stretch=1)
        src_row.addWidget(btn_browse)
        c_layout.addLayout(src_row)

        level_row = QHBoxLayout()
        level_row.addWidget(QLabel("Compression Preset:"))
        self.comp_level_combo = QComboBox()
        self.comp_level_combo.addItems(
            [
                "Low — Lossless stream & font cleanup (100% original image quality)",
                "Medium — Balanced image optimization (1600px max, Q75)",
                "High — Maximum size reduction (1100px max, Q52)",
            ]
        )
        self.comp_level_combo.setCurrentIndex(1)
        level_row.addWidget(self.comp_level_combo, stretch=1)
        c_layout.addLayout(level_row)

        note = QLabel(
            "Note: Image-heavy and scanned PDFs shrink significantly with Medium/High presets. "
            "Purely text-based PDFs rely on lossless stream deflation and may see smaller reductions."
        )
        note.setProperty("class", "muted")
        note.setWordWrap(True)
        c_layout.addWidget(note)

        btn_run = QPushButton("Compress & Save As...")
        btn_run.setObjectName("PrimaryBtn")
        btn_run.clicked.connect(self._execute_compress)
        c_layout.addWidget(btn_run)

        self.comp_result_label = QLabel("")
        self.comp_result_label.setStyleSheet("font-weight: 600;")
        c_layout.addWidget(self.comp_result_label)

        layout.addWidget(card)
        layout.addStretch()
        return tab

    def _execute_compress(self) -> None:
        src_str = self.comp_src_edit.text().strip()
        if not src_str:
            QMessageBox.warning(self, "Compress PDF", "Choose a source PDF first.")
            return
        src = Path(src_str)
        suggested = src.with_name(f"{src.stem}_compressed.pdf")
        dest_str, _ = QFileDialog.getSaveFileName(
            self, "Save Compressed PDF As", str(suggested), "PDF Documents (*.pdf)"
        )
        if not dest_str:
            return
        levels = ["low", "medium", "high"]
        chosen_level = levels[self.comp_level_combo.currentIndex()]
        try:
            res = compress_pdf(src, dest_str, chosen_level, self.file_service)
            summary = (
                f"Compressed: {_format_bytes(res.original_bytes)} -> "
                f"{_format_bytes(res.compressed_bytes)} (Saved {res.saved_percent}%)"
            )
            self.comp_result_label.setText(summary)
            self.status_message.emit(summary)
            if QMessageBox.question(
                self, "Compression Complete", f"{summary}\n\nOpen compressed PDF?"
            ) == QMessageBox.StandardButton.Yes:
                self.open_pdf_requested.emit(str(res.output_path))
        except PdfCompressError as exc:
            QMessageBox.critical(self, "Compression Failed", str(exc))

    # --- TAB 2: WATERMARK ---
    def _build_watermark_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(10)

        src_row = QHBoxLayout()
        self.wm_src_edit = QLineEdit()
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(lambda: self._pick_pdf(self.wm_src_edit))
        src_row.addWidget(self.wm_src_edit, stretch=1)
        src_row.addWidget(btn_browse)
        form.addRow("Source PDF:", src_row)

        self.wm_text_edit = QLineEdit("CONFIDENTIAL")
        form.addRow("Watermark Text:", self.wm_text_edit)

        self.wm_size_spin = QSpinBox()
        self.wm_size_spin.setRange(12, 140)
        self.wm_size_spin.setValue(48)
        form.addRow("Font Size (pt):", self.wm_size_spin)

        self.wm_opacity_spin = QDoubleSpinBox()
        self.wm_opacity_spin.setRange(0.05, 1.0)
        self.wm_opacity_spin.setSingleStep(0.05)
        self.wm_opacity_spin.setValue(0.25)
        form.addRow("Opacity (0.05 - 1.0):", self.wm_opacity_spin)

        self.wm_angle_spin = QSpinBox()
        self.wm_angle_spin.setRange(-180, 180)
        self.wm_angle_spin.setValue(45)
        form.addRow("Rotation Angle (°):", self.wm_angle_spin)

        self.wm_color_combo = QComboBox()
        self.wm_color_combo.addItems(list(COLOR_PRESETS.keys()))
        form.addRow("Text Color:", self.wm_color_combo)

        self.wm_pages_edit = QLineEdit()
        self.wm_pages_edit.setPlaceholderText("Leave blank for all pages, or e.g. 1-3, 5")
        form.addRow("Page Range:", self.wm_pages_edit)

        btn_wm = QPushButton("Apply Watermark & Save As...")
        btn_wm.setObjectName("PrimaryBtn")
        btn_wm.clicked.connect(self._execute_watermark)
        form.addRow("", btn_wm)

        layout.addWidget(card)
        layout.addStretch()
        return tab

    def _execute_watermark(self) -> None:
        src_str = self.wm_src_edit.text().strip()
        if not src_str:
            QMessageBox.warning(self, "Watermark", "Choose a source PDF first.")
            return
        src = Path(src_str)
        suggested = src.with_name(f"{src.stem}_watermarked.pdf")
        dest_str, _ = QFileDialog.getSaveFileName(
            self, "Save Watermarked PDF As", str(suggested), "PDF Documents (*.pdf)"
        )
        if not dest_str:
            return
        try:
            saved = add_text_watermark(
                source_path=src,
                output_path=dest_str,
                text=self.wm_text_edit.text(),
                file_service=self.file_service,
                font_size=self.wm_size_spin.value(),
                opacity=self.wm_opacity_spin.value(),
                angle=self.wm_angle_spin.value(),
                color_name=self.wm_color_combo.currentText(),
                page_range_expr=self.wm_pages_edit.text(),
            )
            self.status_message.emit(f"Watermarked PDF saved to {saved.name}")
            if QMessageBox.question(
                self, "Watermark Complete", f"Saved to:\n{saved}\n\nOpen it now?"
            ) == QMessageBox.StandardButton.Yes:
                self.open_pdf_requested.emit(str(saved))
        except PdfWatermarkError as exc:
            QMessageBox.critical(self, "Watermark Failed", str(exc))

    # --- TAB 3: METADATA ---
    def _build_metadata_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        form = QFormLayout(card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(10)

        src_row = QHBoxLayout()
        self.meta_src_edit = QLineEdit()
        btn_browse = QPushButton("Load PDF...")
        btn_browse.clicked.connect(self._browse_and_load_metadata)
        src_row.addWidget(self.meta_src_edit, stretch=1)
        src_row.addWidget(btn_browse)
        form.addRow("Source PDF:", src_row)

        self.meta_title = QLineEdit()
        self.meta_author = QLineEdit()
        self.meta_subject = QLineEdit()
        self.meta_keywords = QLineEdit()
        self.meta_creator = QLineEdit()

        form.addRow("Title:", self.meta_title)
        form.addRow("Author:", self.meta_author)
        form.addRow("Subject:", self.meta_subject)
        form.addRow("Keywords:", self.meta_keywords)
        form.addRow("Creator:", self.meta_creator)

        btn_save_meta = QPushButton("Save Updated Copy As...")
        btn_save_meta.setObjectName("PrimaryBtn")
        btn_save_meta.clicked.connect(self._execute_save_metadata)
        form.addRow("", btn_save_meta)

        layout.addWidget(card)
        layout.addStretch()
        return tab

    def _browse_and_load_metadata(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", str(Path.home()), "PDF Documents (*.pdf)"
        )
        if path:
            self.meta_src_edit.setText(path)
            self._load_metadata_fields(Path(path))

    def _load_metadata_fields(self, path: Path) -> None:
        try:
            meta = read_pdf_metadata(path)
            self.meta_title.setText(meta["title"])
            self.meta_author.setText(meta["author"])
            self.meta_subject.setText(meta["subject"])
            self.meta_keywords.setText(meta["keywords"])
            self.meta_creator.setText(meta["creator"])
        except PdfMetadataError as exc:
            self.status_message.emit(str(exc))

    def _execute_save_metadata(self) -> None:
        src_str = self.meta_src_edit.text().strip()
        if not src_str:
            QMessageBox.warning(self, "Metadata", "Select a source PDF first.")
            return
        src = Path(src_str)
        suggested = src.with_name(f"{src.stem}_metadata.pdf")
        dest_str, _ = QFileDialog.getSaveFileName(
            self, "Save PDF with Updated Metadata", str(suggested), "PDF Documents (*.pdf)"
        )
        if not dest_str:
            return
        payload = {
            "title": self.meta_title.text(),
            "author": self.meta_author.text(),
            "subject": self.meta_subject.text(),
            "keywords": self.meta_keywords.text(),
            "creator": self.meta_creator.text(),
        }
        try:
            saved = write_pdf_metadata(src, dest_str, payload, self.file_service)
            self.status_message.emit(f"Saved metadata copy to {saved.name}")
            QMessageBox.information(self, "Metadata Saved", f"Saved updated PDF to:\n{saved}")
        except PdfMetadataError as exc:
            QMessageBox.critical(self, "Metadata Save Failed", str(exc))

    # --- TAB 4: IMAGES <-> PDF ---
    def _build_convert_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(14)

        # Card A: Images -> PDF
        card_a = QFrame()
        card_a.setProperty("class", "card")
        lay_a = QVBoxLayout(card_a)
        lay_a.setContentsMargins(16, 14, 16, 14)
        lay_a.setSpacing(8)

        lbl_a = QLabel("Images -> PDF (Combine PNG / JPG / WEBP / BMP into one PDF)")
        lbl_a.setProperty("class", "section-title")
        lay_a.addWidget(lbl_a)

        btn_row_a = QHBoxLayout()
        btn_add_imgs = QPushButton("+ Add Images...")
        btn_add_imgs.clicked.connect(self._add_images_for_pdf)
        btn_clear_imgs = QPushButton("Clear")
        btn_clear_imgs.clicked.connect(lambda: self.img_list.clear())
        btn_make_pdf = QPushButton("Convert Images to PDF...")
        btn_make_pdf.setObjectName("PrimaryBtn")
        btn_make_pdf.clicked.connect(self._execute_images_to_pdf)
        btn_row_a.addWidget(btn_add_imgs)
        btn_row_a.addWidget(btn_clear_imgs)
        btn_row_a.addStretch()
        btn_row_a.addWidget(btn_make_pdf)
        lay_a.addLayout(btn_row_a)

        self.img_list = QListWidget()
        self.img_list.setMaximumHeight(130)
        lay_a.addWidget(self.img_list)
        layout.addWidget(card_a)

        # Card B: PDF -> Images
        card_b = QFrame()
        card_b.setProperty("class", "card")
        form_b = QFormLayout(card_b)
        form_b.setContentsMargins(16, 14, 16, 14)
        form_b.setSpacing(10)

        lbl_b = QLabel("PDF -> Images (Export Pages as PNG or JPG)")
        lbl_b.setProperty("class", "section-title")
        form_b.addRow(lbl_b)

        src_row_b = QHBoxLayout()
        self.p2i_src_edit = QLineEdit()
        btn_b_browse = QPushButton("Browse...")
        btn_b_browse.clicked.connect(lambda: self._pick_pdf(self.p2i_src_edit))
        src_row_b.addWidget(self.p2i_src_edit, stretch=1)
        src_row_b.addWidget(btn_b_browse)
        form_b.addRow("Source PDF:", src_row_b)

        self.p2i_fmt_combo = QComboBox()
        self.p2i_fmt_combo.addItems(["PNG (Lossless)", "JPG (Compact)"])
        form_b.addRow("Image Format:", self.p2i_fmt_combo)

        self.p2i_dpi_combo = QComboBox()
        self.p2i_dpi_combo.addItems(["100 DPI (Fast / Screen)", "150 DPI (Standard)", "200 DPI (High Detail)"])
        self.p2i_dpi_combo.setCurrentIndex(1)
        form_b.addRow("Resolution:", self.p2i_dpi_combo)

        self.p2i_pages_edit = QLineEdit()
        self.p2i_pages_edit.setPlaceholderText("Leave blank for all pages, or e.g. 1-5")
        form_b.addRow("Page Range:", self.p2i_pages_edit)

        btn_export_imgs = QPushButton("Export Pages to Folder...")
        btn_export_imgs.setObjectName("PrimaryBtn")
        btn_export_imgs.clicked.connect(self._execute_pdf_to_images)
        form_b.addRow("", btn_export_imgs)

        layout.addWidget(card_b)
        layout.addStretch()
        return tab

    def _pick_pdf(self, target_edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF", str(Path.home()), "PDF Documents (*.pdf)"
        )
        if path:
            target_edit.setText(path)

    def _add_images_for_pdf(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Image Files",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        for p in paths:
            item = QListWidgetItem(p)
            item.setData(256, p)
            self.img_list.addItem(item)

    def _execute_images_to_pdf(self) -> None:
        imgs = [self.img_list.item(i).data(256) for i in range(self.img_list.count())]
        if not imgs:
            QMessageBox.warning(self, "Images to PDF", "Add at least one image first.")
            return
        suggested = Path(imgs[0]).with_name("images_combined.pdf")
        dest_str, _ = QFileDialog.getSaveFileName(
            self, "Save Output PDF As", str(suggested), "PDF Documents (*.pdf)"
        )
        if not dest_str:
            return
        try:
            saved = images_to_pdf(imgs, dest_str, self.file_service)
            self.status_message.emit(f"Created {saved.name} from {len(imgs)} image(s).")
            if QMessageBox.question(
                self, "Conversion Complete", f"Saved PDF to:\n{saved}\n\nOpen it now?"
            ) == QMessageBox.StandardButton.Yes:
                self.open_pdf_requested.emit(str(saved))
        except PdfConvertError as exc:
            QMessageBox.critical(self, "Conversion Failed", str(exc))

    def _execute_pdf_to_images(self) -> None:
        src_str = self.p2i_src_edit.text().strip()
        if not src_str:
            QMessageBox.warning(self, "PDF to Images", "Choose a source PDF first.")
            return
        src = Path(src_str)
        out_dir = QFileDialog.getExistingDirectory(
            self, "Choose Destination Folder for Images", str(src.parent)
        )
        if not out_dir:
            return
        fmt = "png" if self.p2i_fmt_combo.currentIndex() == 0 else "jpg"
        dpi = [100, 150, 200][self.p2i_dpi_combo.currentIndex()]
        try:
            created = pdf_to_images(
                src, out_dir, image_format=fmt, dpi=dpi, page_range_expr=self.p2i_pages_edit.text()
            )
            self.status_message.emit(f"Exported {len(created)} {fmt.upper()} image(s).")
            QMessageBox.information(
                self,
                "Export Complete",
                f"Exported {len(created)} {fmt.upper()} file(s) to:\n{out_dir}",
            )
        except PdfConvertError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
