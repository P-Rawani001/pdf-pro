"""Image-to-PDF and PDF-to-Image conversion utilities."""

from __future__ import annotations

import io
from pathlib import Path

import pymupdf
from PIL import Image

from app.operations.split import parse_page_ranges
from app.services.file_service import FileService


class PdfConvertError(Exception):
    """Raised when Image <-> PDF conversion fails."""


def images_to_pdf(
    image_paths: list[Path | str],
    output_path: Path | str,
    file_service: FileService,
) -> Path:
    """Combine one or more raster images into a multi-page PDF safely."""
    if not image_paths:
        raise PdfConvertError("Select at least one image file.")

    dest = Path(output_path).resolve()
    temp_path = file_service.create_temp_pdf_path(prefix="pdfpro_img2pdf_")
    out_doc = pymupdf.open()

    try:
        for img_item in image_paths:
            img_path = Path(img_item).resolve()
            if not img_path.exists():
                raise PdfConvertError(f"Image not found: {img_path}")

            with Image.open(img_path) as pil_img:
                # Flatten transparency onto white canvas so PNGs convert cleanly
                if pil_img.mode in ("RGBA", "LA", "P"):
                    canvas = Image.new("RGB", pil_img.size, (255, 255, 255))
                    rgba = pil_img.convert("RGBA")
                    canvas.paste(rgba, mask=rgba.split()[3])
                    rgb_img = canvas
                elif pil_img.mode != "RGB":
                    rgb_img = pil_img.convert("RGB")
                else:
                    rgb_img = pil_img.copy()

                w, h = rgb_img.size
                buf = io.BytesIO()
                rgb_img.save(buf, format="JPEG", quality=92)
                img_bytes = buf.getvalue()

            page = out_doc.new_page(width=float(w), height=float(h))
            page.insert_image(page.rect, stream=img_bytes)

        out_doc.save(str(temp_path), deflate=True)
        out_doc.close()
        file_service.safe_replace_or_save(temp_path, dest)
        return dest
    except Exception as exc:
        try:
            out_doc.close()
        except Exception:
            pass
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise PdfConvertError(f"Failed to convert images to PDF: {exc}") from exc


def pdf_to_images(
    source_path: Path | str,
    output_dir: Path | str,
    image_format: str = "png",
    dpi: int = 150,
    page_range_expr: str = "",
) -> list[Path]:
    """Export PDF pages as PNG or JPG images into output_dir."""
    src = Path(source_path).resolve()
    out_folder = Path(output_dir).resolve()
    if not src.exists():
        raise PdfConvertError(f"PDF not found: {src}")

    fmt = image_format.strip().lower()
    if fmt not in ("png", "jpg", "jpeg"):
        raise PdfConvertError(f"Unsupported image format: {image_format}")
    ext = "jpg" if fmt in ("jpg", "jpeg") else "png"

    out_folder.mkdir(parents=True, exist_ok=True)
    scale = max(72, min(300, int(dpi))) / 72.0
    matrix = pymupdf.Matrix(scale, scale)

    created: list[Path] = []
    try:
        with pymupdf.open(str(src)) as doc:
            if doc.is_encrypted:
                raise PdfConvertError("Cannot export pages from an encrypted PDF.")
            total = len(doc)
            indices = (
                parse_page_ranges(page_range_expr, total)
                if page_range_expr.strip()
                else list(range(total))
            )
            pad = len(str(total))
            for idx in indices:
                page = doc.load_page(idx)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                target = out_folder / f"{src.stem}_page_{str(idx + 1).zfill(pad)}.{ext}"
                if ext == "jpg":
                    pix.save(str(target), jpg_quality=90)
                else:
                    pix.save(str(target))
                created.append(target)
        return created
    except Exception as exc:
        raise PdfConvertError(f"Failed to export PDF pages as images: {exc}") from exc
