"""PDF annotation engine supporting highlight, underline, strikeout, sticky notes, text boxes, and shapes."""

from __future__ import annotations

import pymupdf


class PdfAnnotationError(Exception):
    """Raised when adding or removing PDF annotations fails."""


ANNOTATION_COLORS: dict[str, tuple[float, float, float]] = {
    "Yellow": (1.0, 0.90, 0.15),
    "Cyan": (0.25, 0.84, 0.94),
    "Green": (0.25, 0.85, 0.45),
    "Coral Red": (0.95, 0.35, 0.35),
}


def add_rect_markup(
    doc: pymupdf.Document,
    page_index: int,
    pdf_rect: pymupdf.Rect,
    tool_type: str,
    color_name: str = "Yellow",
    note_text: str = "",
) -> None:
    """Apply an annotation to a PDF page in memory (save via File -> Save Copy)."""
    page = doc.load_page(page_index)
    rgb = ANNOTATION_COLORS.get(color_name, ANNOTATION_COLORS["Yellow"])

    # Ensure minimum sensible dimensions for point/small clicks
    rect = pymupdf.Rect(pdf_rect)
    if rect.width < 4:
        rect.x1 = rect.x0 + 24
    if rect.height < 4:
        rect.y1 = rect.y0 + 24

    try:
        if tool_type == "highlight":
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=rgb)
            annot.update()
        elif tool_type == "underline":
            annot = page.add_underline_annot(rect)
            annot.set_colors(stroke=rgb)
            annot.update()
        elif tool_type == "strikeout":
            annot = page.add_strikeout_annot(rect)
            annot.set_colors(stroke=rgb)
            annot.update()
        elif tool_type == "rectangle":
            annot = page.add_rect_annot(rect)
            annot.set_colors(stroke=rgb)
            annot.set_border(width=2.0)
            annot.update()
        elif tool_type == "sticky_note":
            content = note_text.strip() or "Note"
            annot = page.add_text_annot(rect.tl, content, icon="Comment")
            annot.set_colors(stroke=rgb)
            annot.update()
        elif tool_type == "freetext":
            content = note_text.strip() or "Annotation"
            box = pymupdf.Rect(
                rect.x0,
                rect.y0,
                max(rect.x1, rect.x0 + 180),
                max(rect.y1, rect.y0 + 36),
            )
            annot = page.add_freetext_annot(
                box,
                content,
                fontsize=12,
                fontname="helv",
                text_color=(0.08, 0.12, 0.20),
                fill_color=(1.0, 0.98, 0.82),
                border_color=rgb,
            )
            annot.update()
        else:
            raise PdfAnnotationError(f"Unknown annotation tool: {tool_type}")
    except PdfAnnotationError:
        raise
    except Exception as exc:
        raise PdfAnnotationError(f"Failed to add {tool_type} annotation: {exc}") from exc


def undo_last_annotation_on_page(doc: pymupdf.Document, page_index: int) -> bool:
    """Remove the most recently added annotation on page_index. Returns True if removed."""
    page = doc.load_page(page_index)
    annots = list(page.annots() or [])
    if not annots:
        return False
    page.delete_annot(annots[-1])
    return True
