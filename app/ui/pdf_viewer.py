"""Interactive PDF page canvas with zoom, fit modes, search highlights, text selection, and annotations."""

from __future__ import annotations

import pymupdf
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QGuiApplication,
    QMouseEvent,
    QPainter,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.config import DEFAULT_ZOOM, MAX_ZOOM, MIN_ZOOM, RENDER_DPI_BASE, ZOOM_STEP
from app.core.annotation_manager import (
    PdfAnnotationError,
    add_rect_markup,
    undo_last_annotation_on_page,
)
from app.core.document_manager import PdfDocumentSession, SearchHit
from app.core.pdf_renderer import PdfRenderer


class PageCanvasLabel(QLabel):
    """Displays a rendered PDF page and captures drag rectangles for text copy or annotations."""

    region_dragged = Signal(QRect, str)
    copy_page_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self._dragging = False
        self._start_pt = QPoint()
        self._end_pt = QPoint()
        self._selection_rect = QRect()

    def clear_selection(self) -> None:
        self._selection_rect = QRect()
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._start_pt = event.position().toPoint()
            self._end_pt = self._start_pt
            self._selection_rect = QRect()
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._end_pt = event.position().toPoint()
            self._selection_rect = QRect(self._start_pt, self._end_pt).normalized()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            self._end_pt = event.position().toPoint()
            self._selection_rect = QRect(self._start_pt, self._end_pt).normalized()
            self.update()
            self.region_dragged.emit(self._selection_rect, "auto")
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._selection_rect.isNull() and self._selection_rect.isValid():
            painter = QPainter(self)
            painter.setPen(QPen(QColor("#60D5E8"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(77, 124, 255, 65))
            painter.drawRect(self._selection_rect)
            painter.end()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        act_copy_sel = QAction("Copy Selected Region Text", self)
        act_copy_sel.setEnabled(not self._selection_rect.isNull())
        act_copy_sel.triggered.connect(
            lambda: self.region_dragged.emit(self._selection_rect, "copy_now")
        )

        act_copy_page = QAction("Copy Entire Page Text", self)
        act_copy_page.triggered.connect(self.copy_page_requested.emit)

        menu.addAction(act_copy_sel)
        menu.addAction(act_copy_page)
        menu.exec(event.globalPos())


class PdfViewerWidget(QScrollArea):
    """Scrollable single-tab PDF viewer supporting zoom, search, text copy, and annotations."""

    page_changed = Signal(int, int)
    zoom_changed = Signal(float)
    status_message = Signal(str)
    document_modified = Signal()
    text_selection_changed = Signal(str)

    def __init__(self, session: PdfDocumentSession, renderer: PdfRenderer, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.renderer = renderer
        self._search_hits: list[SearchHit] = []
        self._current_hit_index: int = -1
        self._last_selected_text: str = ""
        self._interaction_mode: str = "select"
        self._annot_color: str = "Yellow"

        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.canvas = PageCanvasLabel()
        self.canvas.region_dragged.connect(self._on_region_dragged)
        self.canvas.copy_page_requested.connect(self.copy_current_page_text)
        layout.addWidget(self.canvas)

        self.setWidget(container)
        self.render_current_page()

    def set_interaction_mode(self, mode: str, color_name: str = "Yellow") -> None:
        self._interaction_mode = mode
        self._annot_color = color_name
        cursor = (
            Qt.CursorShape.IBeamCursor
            if mode == "select"
            else Qt.CursorShape.CrossCursor
        )
        self.canvas.setCursor(cursor)

    def render_current_page(self) -> None:
        page_idx = self.session.current_page
        page_highlights = [
            h.rect for h in self._search_hits if h.page_index == page_idx
        ]
        pixmap = self.renderer.render_page(
            self.session.doc,
            page_idx,
            zoom=self.session.zoom,
            highlights=page_highlights or None,
        )
        self.canvas.setPixmap(pixmap)
        self.canvas.resize(pixmap.size())
        self.page_changed.emit(page_idx + 1, self.session.page_count)
        self.zoom_changed.emit(self.session.zoom)

    def go_to_page(self, page_1based: int) -> None:
        target = max(0, min(self.session.page_count - 1, page_1based - 1))
        if target != self.session.current_page:
            self.session.current_page = target
            self.canvas.clear_selection()
            self.verticalScrollBar().setValue(0)
            self.render_current_page()

    def next_page(self) -> None:
        self.go_to_page(self.session.current_page + 2)

    def prev_page(self) -> None:
        self.go_to_page(self.session.current_page)

    def set_zoom(self, new_zoom: float) -> None:
        clamped = max(MIN_ZOOM, min(MAX_ZOOM, round(new_zoom, 2)))
        if clamped != self.session.zoom:
            self.session.zoom = clamped
            self.canvas.clear_selection()
            self.render_current_page()

    def zoom_in(self) -> None:
        self.set_zoom(self.session.zoom + ZOOM_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self.session.zoom - ZOOM_STEP)

    def reset_zoom(self) -> None:
        self.set_zoom(DEFAULT_ZOOM)

    def fit_width(self) -> None:
        page_w_pt, _ = self.session.get_page_size_points(self.session.current_page)
        base_px = page_w_pt * (RENDER_DPI_BASE / 72.0)
        available_w = max(200, self.viewport().width() - 64)
        self.set_zoom(available_w / max(1.0, base_px))

    def fit_page(self) -> None:
        page_w_pt, page_h_pt = self.session.get_page_size_points(self.session.current_page)
        scale_base = RENDER_DPI_BASE / 72.0
        avail_w = max(200, self.viewport().width() - 64)
        avail_h = max(200, self.viewport().height() - 64)
        zoom_w = avail_w / max(1.0, page_w_pt * scale_base)
        zoom_h = avail_h / max(1.0, page_h_pt * scale_base)
        self.set_zoom(min(zoom_w, zoom_h))

    def search(self, query: str) -> None:
        cleaned = query.strip()
        if not cleaned:
            self._search_hits.clear()
            self._current_hit_index = -1
            self.render_current_page()
            self.status_message.emit("Search cleared.")
            return

        if (
            self._search_hits
            and getattr(self, "_last_query", "") == cleaned.lower()
        ):
            self._current_hit_index = (self._current_hit_index + 1) % len(self._search_hits)
        else:
            self._last_query = cleaned.lower()
            self._search_hits = self.session.search_text(cleaned)
            self._current_hit_index = 0 if self._search_hits else -1

        if not self._search_hits:
            self.render_current_page()
            self.status_message.emit(f"No matches found for '{cleaned}'.")
            return

        hit = self._search_hits[self._current_hit_index]
        self.session.current_page = hit.page_index
        self.render_current_page()
        self.status_message.emit(
            f"Match {self._current_hit_index + 1} of {len(self._search_hits)} "
            f"(Page {hit.page_index + 1})"
        )

    def _on_region_dragged(self, rect: QRect, action_mode: str) -> None:
        scale = (RENDER_DPI_BASE / 72.0) * self.session.zoom
        pdf_rect = pymupdf.Rect(
            rect.left() / scale,
            rect.top() / scale,
            rect.right() / scale,
            rect.bottom() / scale,
        )

        if self._interaction_mode == "select" or action_mode == "copy_now":
            if rect.width() <= 6 or rect.height() <= 6:
                return
            extracted = self.session.extract_text_in_rect(self.session.current_page, pdf_rect)
            self._last_selected_text = extracted
            self.text_selection_changed.emit(extracted)
            if extracted:
                QGuiApplication.clipboard().setText(extracted)
                preview = extracted[:60].replace("\n", " ")
                self.status_message.emit(f"Copied to clipboard: \"{preview}...\"")
            elif action_mode == "copy_now":
                self.status_message.emit("No selectable text in drawn region (page may be scanned).")
            return

        note_text = ""
        if self._interaction_mode in ("sticky_note", "freetext"):
            prompt_title = "Sticky Note Content" if self._interaction_mode == "sticky_note" else "Text Box Content"
            txt, ok = QInputDialog.getText(self, prompt_title, "Enter annotation text:")
            if not ok or not txt.strip():
                self.canvas.clear_selection()
                return
            note_text = txt.strip()
        elif rect.width() <= 4 or rect.height() <= 4:
            self.canvas.clear_selection()
            return

        try:
            add_rect_markup(
                self.session.doc,
                self.session.current_page,
                pdf_rect,
                tool_type=self._interaction_mode,
                color_name=self._annot_color,
                note_text=note_text,
            )
            self.session.is_dirty = True
            self.canvas.clear_selection()
            self.renderer.invalidate_document(self.session.doc)
            self.render_current_page()
            self.document_modified.emit()
            self.status_message.emit(
                f"Added {self._interaction_mode.replace('_', ' ')} on Page {self.session.current_page + 1} (use Save Copy to export)."
            )
        except PdfAnnotationError as exc:
            QMessageBox.warning(self, "Annotation Failed", str(exc))

    def undo_last_annotation(self) -> None:
        if undo_last_annotation_on_page(self.session.doc, self.session.current_page):
            self.renderer.invalidate_document(self.session.doc)
            self.render_current_page()
            self.document_modified.emit()
            self.status_message.emit("Removed last annotation on current page.")
        else:
            self.status_message.emit("No annotations to undo on this page.")

    def copy_selected_or_page_text(self) -> None:
        if self._last_selected_text:
            QGuiApplication.clipboard().setText(self._last_selected_text)
            self.status_message.emit("Copied selected text to clipboard.")
        else:
            self.copy_current_page_text()

    def copy_current_page_text(self) -> None:
        txt = self.session.get_page_text(self.session.current_page).strip()
        if txt:
            QGuiApplication.clipboard().setText(txt)
            self.status_message.emit(
                f"Copied all text from Page {self.session.current_page + 1} ({len(txt)} chars)."
            )
        else:
            self.status_message.emit("Page contains no embedded text.")

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)
