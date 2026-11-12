"""Non-destructive virtual page plan (reorder, rotate, delete, extract) and atomic commit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pymupdf

from app.services.file_service import FileService


class PageOperationError(Exception):
    """Raised when a page organization operation is invalid."""


@dataclass
class PagePlanItem:
    """Represents one planned page entry referencing an original 0-based page index."""

    source_page_index: int
    rotation_delta: int = 0


class PagePlan:
    """In-memory page arrangement supporting reorder, rotate, delete, and build."""

    def __init__(self, total_pages: int) -> None:
        if total_pages <= 0:
            raise PageOperationError("Document must have at least 1 page.")
        self.items: list[PagePlanItem] = [
            PagePlanItem(source_page_index=i, rotation_delta=0)
            for i in range(total_pages)
        ]

    def reset(self, total_pages: int) -> None:
        self.items = [
            PagePlanItem(source_page_index=i, rotation_delta=0)
            for i in range(total_pages)
        ]

    def rotate_positions(self, positions: list[int], delta_degrees: int) -> None:
        for pos in positions:
            if 0 <= pos < len(self.items):
                self.items[pos].rotation_delta = (
                    self.items[pos].rotation_delta + delta_degrees
                ) % 360

    def delete_positions(self, positions: list[int]) -> None:
        to_remove = set(positions)
        remaining = [
            item for idx, item in enumerate(self.items) if idx not in to_remove
        ]
        if not remaining:
            raise PageOperationError("Cannot delete all pages from a PDF.")
        self.items = remaining

    def move_up(self, position: int) -> int:
        if position <= 0 or position >= len(self.items):
            return position
        self.items[position - 1], self.items[position] = (
            self.items[position],
            self.items[position - 1],
        )
        return position - 1

    def move_down(self, position: int) -> int:
        if position < 0 or position >= len(self.items) - 1:
            return position
        self.items[position + 1], self.items[position] = (
            self.items[position],
            self.items[position + 1],
        )
        return position + 1

    def build_output_pdf(
        self,
        source_doc: pymupdf.Document,
        destination: Path,
        file_service: FileService,
        selected_positions: list[int] | None = None,
    ) -> Path:
        """Write either the full planned document or selected positions safely via temp file."""
        target_items = (
            [self.items[p] for p in selected_positions if 0 <= p < len(self.items)]
            if selected_positions is not None
            else self.items
        )
        if not target_items:
            raise PageOperationError("No pages selected to save.")

        out_doc = pymupdf.open()
        temp_path = file_service.create_temp_pdf_path(prefix="pdfpro_org_")
        try:
            for item in target_items:
                out_doc.insert_pdf(
                    source_doc,
                    from_page=item.source_page_index,
                    to_page=item.source_page_index,
                )
                if item.rotation_delta:
                    new_page = out_doc[-1]
                    new_page.set_rotation((new_page.rotation + item.rotation_delta) % 360)

            out_doc.save(str(temp_path), garbage=3, deflate=True)
            out_doc.close()
            file_service.safe_replace_or_save(temp_path, destination)
            return destination
        except Exception as exc:
            try:
                out_doc.close()
            except Exception:
                pass
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise PageOperationError(f"Failed to build organized PDF: {exc}") from exc
