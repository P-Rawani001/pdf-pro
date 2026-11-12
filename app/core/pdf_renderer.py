"""Memory-bounded PyMuPDF rendering engine with LRU caching for pages and thumbnails."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

import pymupdf
from PySide6.QtGui import QImage, QPixmap

from app.config import (
    PIXMAP_CACHE_MAX_PAGES,
    RENDER_DPI_BASE,
    THUMBNAIL_CACHE_MAX_PAGES,
    THUMBNAIL_WIDTH_PX,
)


@dataclass(frozen=True)
class RenderKey:
    """Cache key uniquely identifying a rendered PDF page state."""

    doc_id: int
    page_index: int
    zoom_bucket: int
    rotation: int


class PdfRenderer:
    """Thread-safe, LRU-cached renderer converting PyMuPDF pages into QPixmaps."""

    def __init__(
        self,
        max_page_cache: int = PIXMAP_CACHE_MAX_PAGES,
        max_thumb_cache: int = THUMBNAIL_CACHE_MAX_PAGES,
    ) -> None:
        self.max_page_cache = max_page_cache
        self.max_thumb_cache = max_thumb_cache
        self._page_cache: OrderedDict[RenderKey, QPixmap] = OrderedDict()
        self._thumb_cache: OrderedDict[tuple[int, int, int], QPixmap] = OrderedDict()

    def render_page(
        self,
        doc: pymupdf.Document,
        page_index: int,
        zoom: float = 1.0,
        highlights: list[pymupdf.Rect] | None = None,
    ) -> QPixmap:
        """Render a page at the requested zoom level, using LRU cache when no transient highlights exist."""
        page = doc.load_page(page_index)
        zoom_bucket = int(round(zoom * 100))
        key = RenderKey(id(doc), page_index, zoom_bucket, page.rotation)

        if not highlights and key in self._page_cache:
            self._page_cache.move_to_end(key)
            return self._page_cache[key]

        scale = (RENDER_DPI_BASE / 72.0) * zoom
        matrix = pymupdf.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        qimg = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format.Format_RGB888,
        ).copy()
        qpixmap = QPixmap.fromImage(qimg)

        if highlights:
            from PySide6.QtGui import QColor, QPainter

            painter = QPainter(qpixmap)
            painter.setBrush(QColor(255, 230, 0, 105))
            painter.setPen(QColor(255, 190, 0, 210))
            for rect in highlights:
                painter.drawRect(
                    int(rect.x0 * scale),
                    int(rect.y0 * scale),
                    max(4, int((rect.x1 - rect.x0) * scale)),
                    max(4, int((rect.y1 - rect.y0) * scale)),
                )
            painter.end()
            return qpixmap

        self._page_cache[key] = qpixmap
        self._page_cache.move_to_end(key)
        while len(self._page_cache) > self.max_page_cache:
            self._page_cache.popitem(last=False)
        return qpixmap

    def render_thumbnail(
        self, doc: pymupdf.Document, page_index: int, width_px: int = THUMBNAIL_WIDTH_PX
    ) -> QPixmap:
        """Render a lightweight page thumbnail for the sidebar/inspector."""
        page = doc.load_page(page_index)
        cache_key = (id(doc), page_index, page.rotation)
        if cache_key in self._thumb_cache:
            self._thumb_cache.move_to_end(cache_key)
            return self._thumb_cache[cache_key]

        rect = page.rect
        scale = width_px / max(1.0, rect.width)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        qimg = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format.Format_RGB888,
        ).copy()
        qpixmap = QPixmap.fromImage(qimg)

        self._thumb_cache[cache_key] = qpixmap
        self._thumb_cache.move_to_end(cache_key)
        while len(self._thumb_cache) > self.max_thumb_cache:
            self._thumb_cache.popitem(last=False)
        return qpixmap

    def invalidate_document(self, doc: pymupdf.Document) -> None:
        """Evict all cached pixmaps belonging to a closed or modified document."""
        doc_id = id(doc)
        self._page_cache = OrderedDict(
            (k, v) for k, v in self._page_cache.items() if k.doc_id != doc_id
        )
        self._thumb_cache = OrderedDict(
            (k, v) for k, v in self._thumb_cache.items() if k[0] != doc_id
        )
