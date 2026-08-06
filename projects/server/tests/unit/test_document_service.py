"""DocumentService unit tests."""

from pathlib import Path

import pytest

from src.common.exceptions import NotFoundException
from src.document.domains import BBox, DetectionBlock
from src.document.pipeline.label_map import map_label
from src.document.pipeline.paddle_engine import _html_table_to_markdown, _normalize_bbox
from src.document.pipeline.docling_engine import map_docling_label
from src.document.pipeline.pymupdf_engine import SOURCE_PDF_NAME, extract_native_blocks
from src.document.pipeline.vision_llm_engine import normalize_engine_name, parse_vision_blocks
from src.document.service import DocumentService, _read_image_size, _stub_blocks_for_page
from src.document.settings import DocumentSettings


class FakePipeline:
    available = True
    init_error = None

    def __init__(self, blocks_factory=None) -> None:
        self._blocks_factory = blocks_factory

    async def detect_page(self, **kwargs):
        if self._blocks_factory:
            return self._blocks_factory(**kwargs)
        start = kwargs["start_index"]
        page = kwargs["page_number"]
        return [
            DetectionBlock(
                id=str(start),
                index=start,
                page=page,
                type="text",
                bbox=BBox(0.1, 0.1, 0.5, 0.1),
                markdown=f"real page {page}",
            )
        ]


@pytest.fixture
def service(tmp_path: Path) -> DocumentService:
    settings = DocumentSettings(DOCUMENT_USE_STUB_FALLBACK=True)
    return DocumentService(upload_dir=tmp_path, pipeline=FakePipeline(), settings=settings)


@pytest.mark.unit
def test_stub_blocks_include_all_types() -> None:
    blocks = _stub_blocks_for_page(page_number=1, start_index=1, variant="default")
    types = {b.type for b in blocks}
    assert types == {"text", "figure", "table", "marginalia"}
    assert all(b.page == 1 for b in blocks)


@pytest.mark.unit
def test_label_map() -> None:
    assert map_label("table") == "table"
    assert map_label("figure") == "figure"
    assert map_label("footer") == "marginalia"
    assert map_label("title") == "text"
    assert map_label("logo") == "logo"
    assert map_label("unknown_xyz") is None


@pytest.mark.unit
def test_normalize_engine_name() -> None:
    assert normalize_engine_name("layout-ocr") == "paddle"
    assert normalize_engine_name("paddle_llm") == "paddle_llm"
    assert normalize_engine_name("vision-llm") == "vision_llm"
    assert normalize_engine_name("Vision LLM") == "vision_llm"
    assert normalize_engine_name("pymupdf") == "pymupdf"
    assert normalize_engine_name("pymupdf-ocr") == "pymupdf_ocr"
    assert normalize_engine_name("docling") == "docling"
    assert normalize_engine_name("unknown_engine") == "paddle"


@pytest.mark.unit
def test_map_docling_label() -> None:
    assert map_docling_label("TEXT") == "text"
    assert map_docling_label("section_header") == "text"
    assert map_docling_label("TABLE") == "table"
    assert map_docling_label("PICTURE") == "figure"
    assert map_docling_label("PAGE_FOOTER") == "marginalia"
    assert map_docling_label("unknown") is None


@pytest.mark.unit
def test_extract_native_blocks_from_pdf(tmp_path: Path) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=400, height=600)
    page.insert_text((72, 72), "Hello native PDF")
    page.insert_text((72, 560), "1")
    pdf_path = tmp_path / SOURCE_PDF_NAME
    pdf_path.write_bytes(doc.tobytes())
    doc.close()

    blocks, chars = extract_native_blocks(pdf_path=pdf_path, page_number=1, start_index=1)
    assert chars > 0
    assert any("Hello native PDF" in b.markdown for b in blocks)


@pytest.mark.unit
def test_parse_vision_blocks() -> None:
    payload = {
        "blocks": [
            {
                "category": "heading",
                "bbox": [0.3, 0.15, 0.7, 0.2],
                "markdown": "개정 이력",
                "html": "",
            },
            {
                "category": "table",
                "bbox": [0.1, 0.22, 0.9, 0.55],
                "markdown": "| A |\n| --- |\n| 1 |",
                "html": "<table><tr><td>A</td></tr><tr><td>1</td></tr></table>",
            },
            {
                "category": "footer",
                "bbox": [0.1, 0.9, 0.4, 0.95],
                "markdown": "일반현황 _ 7",
                "html": "",
            },
            {
                "category": "logo",
                "bbox": [0.1, 0.05, 0.25, 0.12],
                "markdown": "![logo](logo)",
                "html": "",
            },
            {
                "category": "paragraph",
                "bbox": [0.0, 0.0, 1.0, 1.0],
                "markdown": "too big",
                "html": "",
            },
        ]
    }
    blocks = parse_vision_blocks(payload, page_number=1, start_index=1)
    types = {b.type for b in blocks}
    assert types == {"text", "table", "marginalia", "logo"}
    table = next(b for b in blocks if b.type == "table")
    assert "<table" in table.html


@pytest.mark.unit
def test_normalize_bbox_and_html_table() -> None:
    box = _normalize_bbox(100, 200, 300, 400, width=1000, height=1000)
    assert box == BBox(0.1, 0.2, 0.2, 0.2)
    md = _html_table_to_markdown("<table><tr><td>A</td><td>B</td></tr><tr><td>1</td><td>2</td></tr></table>")
    assert "| A | B |" in md
    assert "| 1 | 2 |" in md


@pytest.mark.unit
def test_list_samples(service: DocumentService) -> None:
    samples = service.list_samples()
    assert len(samples) >= 2
    assert {s.sample_id for s in samples} >= {"fiscal-page", "tax-guide"}


@pytest.mark.unit
async def test_detect_upload_uses_pipeline(service: DocumentService) -> None:
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    result = await service.detect_upload(filename="tiny.png", content=png)
    assert result.page_count == 1
    assert result.blocks[0].markdown == "real page 1"
    assert Path(result.pages[0].image_path).is_file()


@pytest.mark.unit
async def test_detect_upload_pdf_all_pages(tmp_path: Path) -> None:
    import fitz

    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), f"hello page {i + 1}")
    pdf_bytes = doc.tobytes()
    doc.close()

    settings = DocumentSettings(DOCUMENT_USE_STUB_FALLBACK=True)
    svc = DocumentService(upload_dir=tmp_path, pipeline=FakePipeline(), settings=settings)
    result = await svc.detect_upload(filename="sample.pdf", content=pdf_bytes)
    assert result.page_count == 3
    assert [b.page for b in result.blocks] == [1, 2, 3]
    page2 = await svc.get_page_image_path(result.document_id, 2)
    assert page2.is_file()
    assert (tmp_path / str(result.document_id) / SOURCE_PDF_NAME).is_file()


@pytest.mark.unit
async def test_detect_upload_pymupdf_native(tmp_path: Path) -> None:
    import fitz

    from src.document.pipeline.engine import LayoutOcrPipeline

    doc = fitz.open()
    page = doc.new_page(width=400, height=600)
    page.insert_text((72, 100), "PyMuPDF pipeline works")
    pdf_bytes = doc.tobytes()
    doc.close()

    settings = DocumentSettings(DOCUMENT_USE_STUB_FALLBACK=False)
    pipeline = LayoutOcrPipeline(settings)
    svc = DocumentService(upload_dir=tmp_path, pipeline=pipeline, settings=settings)
    result = await svc.detect_upload(filename="native.pdf", content=pdf_bytes, engine="pymupdf")
    assert result.page_count == 1
    assert any("PyMuPDF pipeline works" in b.markdown for b in result.blocks)


@pytest.mark.unit
async def test_detect_upload_rejects_unsupported(service: DocumentService) -> None:
    from src.common.exceptions import BadRequestException

    with pytest.raises(BadRequestException):
        await service.detect_upload(filename="note.docx", content=b"PK\x03\x04fake")


@pytest.mark.unit
async def test_detect_falls_back_to_stub(tmp_path: Path) -> None:
    class EmptyPipeline:
        available = True
        init_error = None

        async def detect_page(self, **kwargs):
            return []

    settings = DocumentSettings(DOCUMENT_USE_STUB_FALLBACK=True)
    svc = DocumentService(upload_dir=tmp_path, pipeline=EmptyPipeline(), settings=settings)
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    result = await svc.detect_upload(filename="tiny.png", content=png)
    assert any(b.type == "table" for b in result.blocks)


@pytest.mark.unit
async def test_vision_mode_skips_stub(tmp_path: Path) -> None:
    class EmptyPipeline:
        available = True
        init_error = None

        async def detect_page(self, **kwargs):
            return []

    settings = DocumentSettings(DOCUMENT_USE_STUB_FALLBACK=True)
    svc = DocumentService(upload_dir=tmp_path, pipeline=EmptyPipeline(), settings=settings)
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    result = await svc.detect_upload(filename="tiny.png", content=png, engine="vision_llm")
    assert result.blocks == []


@pytest.mark.unit
async def test_detect_sample(service: DocumentService) -> None:
    result = await service.detect_sample("fiscal-page")
    assert result.page_count == 1
    assert len(result.blocks) >= 1
    image = await service.get_image_path(result.document_id)
    assert image.is_file()


@pytest.mark.unit
async def test_get_document_not_found(service: DocumentService) -> None:
    from src.utils import new_uuid

    with pytest.raises(NotFoundException):
        await service.get_document(new_uuid())


@pytest.mark.unit
def test_read_image_size_fallback(tmp_path: Path) -> None:
    path = tmp_path / "x.bin"
    path.write_bytes(b"not-an-image")
    assert _read_image_size(path) == (900, 1200)
