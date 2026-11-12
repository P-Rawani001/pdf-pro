"""PDF split and page-range extraction utilities using pypdf."""

from __future__ import annotations

from pathlib import Path
from pypdf import PdfReader, PdfWriter

from app.services.file_service import FileService


class PdfSplitError(Exception):
    """Raised when splitting or extracting pages fails."""


def parse_page_ranges(range_expr: str, total_pages: int) -> list[int]:
    """Parse 1-based range string like '1-3, 5, 8-10' into sorted unique 0-based indices."""
    cleaned = range_expr.strip()
    if not cleaned:
        raise PdfSplitError("Enter a page range (e.g., '1-3, 5').")

    indices: list[int] = []
    seen: set[int] = set()

    for part in cleaned.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            bounds = token.split("-", 1)
            if len(bounds) != 2 or not bounds[0].strip().isdigit() or not bounds[1].strip().isdigit():
                raise PdfSplitError(f"Invalid page range segment: '{token}'")
            start_1 = int(bounds[0].strip())
            end_1 = int(bounds[1].strip())
            if start_1 < 1 or end_1 > total_pages or start_1 > end_1:
                raise PdfSplitError(
                    f"Range '{token}' is out of bounds (document has {total_pages} pages)."
                )
            for p in range(start_1 - 1, end_1):
                if p not in seen:
                    seen.add(p)
                    indices.append(p)
        else:
            if not token.isdigit():
                raise PdfSplitError(f"Invalid page number: '{token}'")
            page_1 = int(token)
            if page_1 < 1 or page_1 > total_pages:
                raise PdfSplitError(
                    f"Page {page_1} is out of bounds (document has {total_pages} pages)."
                )
            idx = page_1 - 1
            if idx not in seen:
                seen.add(idx)
                indices.append(idx)

    if not indices:
        raise PdfSplitError("No valid pages specified.")
    return indices


def extract_pages_to_pdf(
    source_path: Path | str,
    page_indices_0based: list[int],
    output_path: Path | str,
    file_service: FileService,
) -> Path:
    """Extract specified 0-based page indices (preserving order) into a new PDF."""
    if not page_indices_0based:
        raise PdfSplitError("Select at least one page to extract.")

    src = Path(source_path).resolve()
    dest = Path(output_path).resolve()
    reader = PdfReader(str(src))
    if reader.is_encrypted:
        raise PdfSplitError("Cannot split an encrypted PDF directly.")

    total = len(reader.pages)
    writer = PdfWriter()
    for idx in page_indices_0based:
        if idx < 0 or idx >= total:
            raise PdfSplitError(f"Page index {idx + 1} out of range (1..{total}).")
        writer.add_page(reader.pages[idx])

    temp_path = file_service.create_temp_pdf_path(prefix="pdfpro_extract_")
    try:
        with open(temp_path, "wb") as f_out:
            writer.write(f_out)
        file_service.safe_replace_or_save(temp_path, dest)
        return dest
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise PdfSplitError(f"Failed to extract pages: {exc}") from exc


def split_into_single_pages(
    source_path: Path | str,
    output_dir: Path | str,
    file_service: FileService,
) -> list[Path]:
    """Split every page of a PDF into individual numbered PDF files in output_dir."""
    src = Path(source_path).resolve()
    out_folder = Path(output_dir).resolve()
    out_folder.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(src))
    if reader.is_encrypted:
        raise PdfSplitError("Cannot split an encrypted PDF directly.")

    total = len(reader.pages)
    if total == 0:
        raise PdfSplitError("Source PDF has 0 pages.")

    pad = len(str(total))
    created_files: list[Path] = []
    for idx, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        target = out_folder / f"{src.stem}_page_{str(idx).zfill(pad)}.pdf"
        temp_path = file_service.create_temp_pdf_path(prefix="pdfpro_split_")
        try:
            with open(temp_path, "wb") as f_out:
                writer.write(f_out)
            file_service.safe_replace_or_save(temp_path, target)
            created_files.append(target)
        except Exception as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise PdfSplitError(f"Failed while writing page {idx}: {exc}") from exc

    return created_files
