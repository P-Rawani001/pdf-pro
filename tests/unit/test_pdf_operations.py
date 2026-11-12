import hashlib
from pathlib import Path
import pymupdf
import pytest
from PIL import Image
from app.ai.document_parser import extract_relevant_context
from app.core.annotation_manager import add_rect_markup, undo_last_annotation_on_page
from app.core.document_manager import PdfOpenError, open_pdf_session
from app.core.metadata_manager import read_pdf_metadata, write_pdf_metadata
from app.core.page_manager import PageOperationError, PagePlan
from app.operations.compress import compress_pdf
from app.operations.convert import images_to_pdf, pdf_to_images
from app.operations.merge import merge_pdfs
from app.operations.split import PdfSplitError, extract_pages_to_pdf, parse_page_ranges, split_into_single_pages
from app.operations.watermark import add_text_watermark
from app.services.file_service import FileService

def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def _make_pdf(p: Path, n: int = 3, prefix: str = "Page") -> Path:
    doc = pymupdf.open()
    for i in range(1, n + 1):
        pg = doc.new_page(width=595, height=842)
        pg.insert_text((72, 100), f"{prefix} {i}: Sample PDF Pro content.", fontsize=14)
    doc.save(str(p))
    doc.close()
    return p

@pytest.fixture()
def fs() -> FileService:
    return FileService()

def test_range_parsing() -> None:
    assert parse_page_ranges("1-3, 5, 2", 6) == [0, 1, 2, 4]
    with pytest.raises(PdfSplitError):
        parse_page_ranges("0-2", 5)
    with pytest.raises(PdfSplitError):
        parse_page_ranges("1-9", 5)

def test_merge_and_split(tmp_path: Path, fs: FileService) -> None:
    a = _make_pdf(tmp_path / "a.pdf", 2, "DocA")
    b = _make_pdf(tmp_path / "b.pdf", 3, "DocB")
    ha, hb = _sha256(a), _sha256(b)
    m = merge_pdfs([a, b], tmp_path / "m.pdf", fs)
    assert _sha256(a) == ha and _sha256(b) == hb
    with pymupdf.open(str(m)) as d:
        assert len(d) == 5
    ext = extract_pages_to_pdf(m, [0, 4], tmp_path / "ext.pdf", fs)
    with pymupdf.open(str(ext)) as d:
        assert len(d) == 2
    parts = split_into_single_pages(b, tmp_path / "splits", fs)
    assert len(parts) == 3

def test_page_plan(tmp_path: Path, fs: FileService) -> None:
    src = _make_pdf(tmp_path / "src.pdf", 3)
    plan = PagePlan(3)
    plan.rotate_positions([0], 90)
    plan.move_down(0)
    plan.delete_positions([2])
    with pytest.raises(PageOperationError):
        plan.delete_positions([0, 1])
    with pymupdf.open(str(src)) as s:
        out = plan.build_output_pdf(s, tmp_path / "org.pdf", fs)
    with pymupdf.open(str(out)) as o:
        assert len(o) == 2 and o[1].rotation == 90

def test_utilities(tmp_path: Path, fs: FileService) -> None:
    src = _make_pdf(tmp_path / "util.pdf", 2)
    c = compress_pdf(src, tmp_path / "c.pdf", "low", fs)
    assert c.compressed_bytes > 0
    w = add_text_watermark(src, tmp_path / "w.pdf", "DRAFT", fs, page_range_expr="1")
    with pymupdf.open(str(w)) as d:
        assert "DRAFT" in d[0].get_text("text")
    m = write_pdf_metadata(src, tmp_path / "m.pdf", {"title": "Spec", "author": "Pankaj"}, fs)
    assert read_pdf_metadata(m)["title"] == "Spec"

def test_images_and_annotations(tmp_path: Path, fs: FileService) -> None:
    img = tmp_path / "sample.png"
    Image.new("RGB", (300, 200), (30, 130, 210)).save(img)
    pdf = images_to_pdf([img], tmp_path / "from_img.pdf", fs)
    exp = pdf_to_images(pdf, tmp_path / "img_out", "png", 100)
    assert len(exp) == 1 and exp[0].exists()
    doc = pymupdf.open(str(pdf))
    add_rect_markup(doc, 0, pymupdf.Rect(20, 20, 120, 60), "highlight", "Yellow")
    assert len(list(doc[0].annots())) == 1
    assert undo_last_annotation_on_page(doc, 0) is True
    assert len(list(doc[0].annots())) == 0
    doc.close()

def test_ai_context_and_corrupt_pdf(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(PdfOpenError):
        open_pdf_session(bad)
    good = _make_pdf(tmp_path / "ai.pdf", 3, "Chapter")
    with pymupdf.open(str(good)) as d:
        ctx, pages = extract_relevant_context(d, query="Chapter 2", current_page_0based=0)
        assert "[Page 2]" in ctx and 2 in pages
