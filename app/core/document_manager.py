"""Document lifecycle, encrypted PDF authentication, text search, and safe saving."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.services.file_service import FileService

logger = logging.getLogger("pdf_pro.document_manager")


class PdfPasswordRequiredError(Exception):
    """Raised when a PDF requires a user password before reading."""


class PdfOpenError(Exception):
    """Raised when a PDF cannot be parsed or is corrupted."""


@dataclass
class SearchHit:
    """Represents a single text search match inside a PDF."""

    page_index: int
    rect: pymupdf.Rect
    snippet: str


class PdfDocumentSession:
    """Wraps an open PyMuPDF document with safe state and query helpers."""

    def __init__(self, file_path: Path, doc: pymupdf.Document) -> None:
        self.file_path = file_path.resolve()
        self.doc = doc
        self.current_page: int = 0
        self.zoom: float = 1.0
        self.is_dirty: bool = False

    @property
    def name(self) -> str:
        return self.file_path.name

    @property
    def page_count(self) -> int:
        return len(self.doc)

    def get_page_size_points(self, page_index: int) -> tuple[float, float]:
        rect = self.doc.load_page(page_index).rect
        return float(rect.width), float(rect.height)

    def get_page_text(self, page_index: int) -> str:
        return self.doc.load_page(page_index).get_text("text")

    def extract_text_in_rect(self, page_index: int, pdf_rect: pymupdf.Rect) -> str:
        """Extract selectable text intersecting a PDF-space rectangle."""
        page = self.doc.load_page(page_index)
        return page.get_textbox(pdf_rect).strip()

    def search_text(self, query: str, max_hits: int = 250) -> list[SearchHit]:
        """Search all pages for case-insensitive occurrences of query."""
        cleaned = query.strip()
        if not cleaned:
            return []
        hits: list[SearchHit] = []
        for page_idx in range(self.page_count):
            page = self.doc.load_page(page_idx)
            rects = page.search_for(cleaned)
            if rects:
                page_txt = page.get_text("text").replace("\n", " ")
                for r in rects:
                    hits.append(
                        SearchHit(
                            page_index=page_idx,
                            rect=r,
                            snippet=f"Page {page_idx + 1}: {page_txt[:90].strip()}...",
                        )
                    )
                    if len(hits) >= max_hits:
                        return hits
        return hits

    def get_metadata(self) -> dict[str, str]:
        raw = self.doc.metadata or {}
        return {
            "Title": raw.get("title") or "",
            "Author": raw.get("author") or "",
            "Subject": raw.get("subject") or "",
            "Keywords": raw.get("keywords") or "",
            "Creator": raw.get("creator") or "",
            "Producer": raw.get("producer") or "",
            "Pages": str(self.page_count),
            "Encrypted": "Yes" if self.doc.is_encrypted else "No",
        }

    def save_copy(self, destination: Path, file_service: FileService) -> None:
        """Atomically save a copy of the PDF via temporary file without clobbering source."""
        temp_path = file_service.create_temp_pdf_path(prefix="pdfpro_save_")
        try:
            self.doc.save(str(temp_path), garbage=3, deflate=True)
            file_service.safe_replace_or_save(temp_path, destination)
            if destination.resolve() == self.file_path:
                self.is_dirty = False
        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

    def close(self) -> None:
        try:
            self.doc.close()
        except Exception as exc:
            logger.debug("Error closing PDF handle: %s", exc)


def open_pdf_session(file_path: Path | str, password: str | None = None) -> PdfDocumentSession:
    """Open and validate a local PDF file safely."""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise PdfOpenError(f"File does not exist: {path}")

    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:
        raise PdfOpenError(f"Unable to open PDF (file may be corrupted): {exc}") from exc

    if doc.needs_pass:
        if not password or not doc.authenticate(password):
            doc.close()
            raise PdfPasswordRequiredError("This PDF is password-protected.")

    if len(doc) == 0:
        doc.close()
        raise PdfOpenError("This PDF contains 0 pages.")

    return PdfDocumentSession(file_path=path, doc=doc)
