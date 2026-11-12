"""Text watermark operation using PyMuPDF vector overlays."""

from __future__ import annotations

from pathlib import Path
import pymupdf

from app.operations.split import parse_page_ranges
from app.services.file_service import FileService


class PdfWatermarkError(Exception):
    """Raised when applying a watermark fails."""


COLOR_PRESETS: dict[str, tuple[float, float, float]] = {
    "Slate Gray": (0.45, 0.48, 0.55),
    "Crimson Red": (0.82, 0.16, 0.18),
    "Royal Blue": (0.18, 0.38, 0.85),
    "Dark Charcoal": (0.15, 0.15, 0.18),
}


def add_text_watermark(
    source_path: Path | str,
    output_path: Path | str,
    text: str,
    file_service: FileService,
    font_size: int = 44,
    opacity: float = 0.25,
    angle: int = 45,
    color_name: str = "Slate Gray",
    page_range_expr: str = "",
) -> Path:
    """Stamp a semi-transparent text watermark onto selected or all pages safely."""
    wm_text = text.strip()
    if not wm_text:
        raise PdfWatermarkError("Watermark text cannot be empty.")

    src = Path(source_path).resolve()
    dest = Path(output_path).resolve()
    if not src.exists() or not src.is_file():
        raise PdfWatermarkError(f"Source file not found: {src}")

    clamped_opacity = max(0.05, min(1.0, float(opacity)))
    rgb = COLOR_PRESETS.get(color_name, COLOR_PRESETS["Slate Gray"])

    temp_path = file_service.create_temp_pdf_path(prefix="pdfpro_wm_")
    doc: pymupdf.Document | None = None
    try:
        doc = pymupdf.open(str(src))
        if doc.is_encrypted:
            raise PdfWatermarkError("Cannot watermark an encrypted PDF. Unlock it first.")

        total = len(doc)
        if page_range_expr.strip():
            target_indices = parse_page_ranges(page_range_expr, total)
        else:
            target_indices = list(range(total))

        for idx in target_indices:
            page = doc.load_page(idx)
            rect = page.rect
            center = pymupdf.Point(rect.width / 2.0, rect.height / 2.0)

            # Calculate approximate text width so watermark centers nicely
            text_len = pymupdf.get_text_length(wm_text, fontname="helv", fontsize=font_size)
            start_pt = pymupdf.Point(center.x - (text_len / 2.0), center.y)

            writer = pymupdf.TextWriter(page.rect)
            writer.append(start_pt, wm_text, font=pymupdf.Font("helv"), fontsize=font_size)
            morph = (center, pymupdf.Matrix(angle))
            writer.write_text(
                page,
                color=rgb,
                opacity=clamped_opacity,
                morph=morph,
                overlay=True,
            )

        doc.save(str(temp_path), garbage=3, deflate=True)
        doc.close()
        doc = None
        file_service.safe_replace_or_save(temp_path, dest)
        return dest
    except Exception as exc:
        if doc is not None:
            doc.close()
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise PdfWatermarkError(f"Failed to apply watermark: {exc}") from exc
