"""PDF merge operation using pypdf with safe temporary file output."""

from __future__ import annotations

from pathlib import Path
from pypdf import PdfReader, PdfWriter

from app.services.file_service import FileService


class PdfMergeError(Exception):
    """Raised when merging PDFs fails."""


def merge_pdfs(
    input_paths: list[Path | str],
    output_path: Path | str,
    file_service: FileService,
) -> Path:
    """Merge multiple PDF files in order into a single output PDF safely."""
    if len(input_paths) < 2:
        raise PdfMergeError("Select at least two PDF files to merge.")

    resolved_inputs = [Path(p).resolve() for p in input_paths]
    destination = Path(output_path).resolve()

    writer = PdfWriter()
    temp_path = file_service.create_temp_pdf_path(prefix="pdfpro_merge_")
    try:
        for pdf_path in resolved_inputs:
            if not pdf_path.exists() or not pdf_path.is_file():
                raise PdfMergeError(f"Input file not found: {pdf_path}")
            reader = PdfReader(str(pdf_path))
            if reader.is_encrypted:
                raise PdfMergeError(
                    f"'{pdf_path.name}' is encrypted. Decrypt or save an unlocked copy first."
                )
            for page in reader.pages:
                writer.add_page(page)

        if len(writer.pages) == 0:
            raise PdfMergeError("Merged document would contain 0 pages.")

        with open(temp_path, "wb") as f_out:
            writer.write(f_out)

        file_service.safe_replace_or_save(temp_path, destination)
        return destination
    except PdfMergeError:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise PdfMergeError(f"Failed to merge PDFs: {exc}") from exc
