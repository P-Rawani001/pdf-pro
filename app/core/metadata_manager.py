"""Read and update PDF document metadata safely without modifying original files."""

from __future__ import annotations

from pathlib import Path
import pymupdf

from app.services.file_service import FileService


class PdfMetadataError(Exception):
    """Raised when reading or updating PDF metadata fails."""


def read_pdf_metadata(source_path: Path | str) -> dict[str, str]:
    """Return normalized metadata fields from a PDF."""
    src = Path(source_path).resolve()
    if not src.exists():
        raise PdfMetadataError(f"File not found: {src}")
    try:
        with pymupdf.open(str(src)) as doc:
            meta = doc.metadata or {}
            return {
                "title": meta.get("title") or "",
                "author": meta.get("author") or "",
                "subject": meta.get("subject") or "",
                "keywords": meta.get("keywords") or "",
                "creator": meta.get("creator") or "",
            }
    except Exception as exc:
        raise PdfMetadataError(f"Could not read metadata: {exc}") from exc


def write_pdf_metadata(
    source_path: Path | str,
    output_path: Path | str,
    metadata: dict[str, str],
    file_service: FileService,
) -> Path:
    """Save a copy of source_path with updated PDF metadata fields."""
    src = Path(source_path).resolve()
    dest = Path(output_path).resolve()
    if not src.exists():
        raise PdfMetadataError(f"File not found: {src}")

    temp_path = file_service.create_temp_pdf_path(prefix="pdfpro_meta_")
    doc: pymupdf.Document | None = None
    try:
        doc = pymupdf.open(str(src))
        if doc.is_encrypted:
            raise PdfMetadataError("Cannot edit metadata of an encrypted PDF.")

        clean_meta = {
            "title": metadata.get("title", "").strip(),
            "author": metadata.get("author", "").strip(),
            "subject": metadata.get("subject", "").strip(),
            "keywords": metadata.get("keywords", "").strip(),
            "creator": metadata.get("creator", "").strip() or "PDF Pro",
        }
        doc.set_metadata(clean_meta)
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
        raise PdfMetadataError(f"Failed to save metadata: {exc}") from exc
