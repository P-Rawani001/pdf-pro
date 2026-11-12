"""PDF compression module supporting lossless structural cleanup and image downsampling."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image

from app.services.file_service import FileService


class PdfCompressError(Exception):
    """Raised when PDF compression fails."""


@dataclass(frozen=True)
class CompressionResult:
    """Summary metrics returned after compressing a PDF."""

    output_path: Path
    original_bytes: int
    compressed_bytes: int

    @property
    def saved_bytes(self) -> int:
        return max(0, self.original_bytes - self.compressed_bytes)

    @property
    def saved_percent(self) -> float:
        if self.original_bytes <= 0:
            return 0.0
        return round((self.saved_bytes / self.original_bytes) * 100.0, 1)


def compress_pdf(
    source_path: Path | str,
    output_path: Path | str,
    level: str,
    file_service: FileService,
) -> CompressionResult:
    """Compress a PDF using 'low' (lossless), 'medium' (balanced), or 'high' (smaller size)."""
    src = Path(source_path).resolve()
    dest = Path(output_path).resolve()
    if not src.exists() or not src.is_file():
        raise PdfCompressError(f"Source file not found: {src}")

    original_size = src.stat().st_size
    normalized = level.strip().lower()
    if normalized not in ("low", "medium", "high"):
        raise PdfCompressError(f"Unsupported compression level: {level}")

    temp_path = file_service.create_temp_pdf_path(prefix="pdfpro_comp_")
    doc: pymupdf.Document | None = None
    try:
        doc = pymupdf.open(str(src))
        if doc.is_encrypted:
            raise PdfCompressError("Cannot compress an encrypted PDF. Unlock it first.")

        if normalized in ("medium", "high"):
            max_dim = 1600 if normalized == "medium" else 1100
            jpeg_quality = 75 if normalized == "medium" else 52
            _downsample_embedded_images(doc, max_dimension=max_dim, jpeg_quality=jpeg_quality)

        doc.save(
            str(temp_path),
            garbage=4,
            deflate=True,
            clean=True,
        )
        doc.close()
        doc = None

        file_service.safe_replace_or_save(temp_path, dest)
        compressed_size = dest.stat().st_size
        return CompressionResult(
            output_path=dest,
            original_bytes=original_size,
            compressed_bytes=compressed_size,
        )
    except PdfCompressError:
        if doc is not None:
            doc.close()
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if doc is not None:
            doc.close()
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise PdfCompressError(f"Compression failed: {exc}") from exc


def _downsample_embedded_images(
    doc: pymupdf.Document, max_dimension: int, jpeg_quality: int
) -> None:
    """Re-encode large embedded raster images to reduce file size while preserving text vectors."""
    processed_xrefs: set[int] = set()
    for page in doc:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            if xref in processed_xrefs:
                continue
            processed_xrefs.add(xref)
            try:
                base_img = doc.extract_image(xref)
                if not base_img:
                    continue
                img_bytes = base_img.get("image")
                if not img_bytes:
                    continue
                # Skip tiny icons/masks
                if len(img_bytes) < 12_000:
                    continue

                with Image.open(io.BytesIO(img_bytes)) as pil_img:
                    w, h = pil_img.size
                    if max(w, h) > max_dimension:
                        scale = max_dimension / float(max(w, h))
                        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
                        pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

                    if pil_img.mode in ("RGBA", "LA", "P"):
                        bg = Image.new("RGB", pil_img.size, (255, 255, 255))
                        converted = pil_img.convert("RGBA")
                        bg.paste(converted, mask=converted.split()[3])
                        pil_img = bg
                    elif pil_img.mode != "RGB":
                        pil_img = pil_img.convert("RGB")

                    buf = io.BytesIO()
                    pil_img.save(buf, format="JPEG", quality=jpeg_quality, optimize=True)
                    new_bytes = buf.getvalue()

                if len(new_bytes) < len(img_bytes):
                    page.replace_image(xref, stream=new_bytes)
            except Exception:
                # Skip exotic color spaces or masks safely without failing the whole document
                continue
