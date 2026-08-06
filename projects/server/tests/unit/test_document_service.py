"""DocumentService unit tests."""

from pathlib import Path

import pytest

from src.common.exceptions import NotFoundException
from src.document.service import DocumentService, _detect_page_elements, _read_image_size


@pytest.fixture
def service(tmp_path: Path) -> DocumentService:
    return DocumentService(upload_dir=tmp_path)


@pytest.mark.unit
def test_detect_page_elements_uses_pdf_content() -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    page.insert_text((30, 25), "Document header")
    page.insert_text((30, 120), "Actual body content")
    page.insert_text((30, 390), "Page footer")

    elements = _detect_page_elements(page, page_number=1)
    doc.close()

    assert {element_type for element_type, _, _ in elements} >= {"text", "marginalia"}
    markdown = "\n".join(content for _, _, content in elements)
    assert "Actual body content" in markdown
    assert "stub" not in markdown
    assert all(0 <= bbox.x <= 1 and 0 <= bbox.y <= 1 for _, bbox, _ in elements)


@pytest.mark.unit
def test_detect_page_elements_finds_table_and_figure() -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=400, height=500)
    for x in (30, 130, 230):
        page.draw_line((x, 80), (x, 180))
    for y in (80, 130, 180):
        page.draw_line((30, y), (230, y))
    page.insert_text((40, 110), "Name")
    page.insert_text((140, 110), "Value")
    page.insert_text((40, 160), "Tax")
    page.insert_text((140, 160), "100")

    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), False)
    pixmap.clear_with(0x336699)
    page.insert_image(fitz.Rect(260, 220, 360, 320), pixmap=pixmap)

    elements = _detect_page_elements(page, page_number=1)
    doc.close()

    types = {element_type for element_type, _, _ in elements}
    assert {"table", "figure"} <= types
    assert any("Name" in content and "Tax" in content for element_type, _, content in elements if element_type == "table")


@pytest.mark.unit
def test_list_samples(service: DocumentService) -> None:
    samples = service.list_samples()
    assert len(samples) >= 2
    assert {s.sample_id for s in samples} >= {"fiscal-page", "tax-guide"}


@pytest.mark.unit
async def test_detect_upload_rejects_image(service: DocumentService) -> None:
    from src.common.exceptions import BadRequestException

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    with pytest.raises(BadRequestException, match="PDF"):
        await service.detect_upload(filename="tiny.png", content=png)


@pytest.mark.unit
async def test_detect_upload_pdf_renders_all_pages(service: DocumentService) -> None:
    import fitz

    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), f"hello page {i + 1}")
    pdf_bytes = doc.tobytes()
    doc.close()

    result = await service.detect_upload(filename="sample.pdf", content=pdf_bytes)
    assert result.filename == "sample.pdf"
    assert result.page_count == 3
    assert len(result.pages) == 3
    assert [p.page_number for p in result.pages] == [1, 2, 3]
    assert all(Path(p.image_path).suffix == ".png" for p in result.pages)
    assert all(Path(p.image_path).is_file() for p in result.pages)
    # indices continue across pages
    indices = [b.index for b in result.blocks]
    assert indices == list(range(1, len(indices) + 1))
    assert {b.page for b in result.blocks} == {1, 2, 3}
    assert all("hello page" in page.blocks[0].markdown for page in result.pages)

    page2 = await service.get_page_image_path(result.document_id, 2)
    assert page2.is_file()


@pytest.mark.unit
async def test_detect_upload_rejects_unsupported(service: DocumentService) -> None:
    from src.common.exceptions import BadRequestException

    with pytest.raises(BadRequestException):
        await service.detect_upload(filename="note.docx", content=b"PK\x03\x04fake")


@pytest.mark.unit
async def test_detect_upload_rejects_spoofed_pdf(service: DocumentService) -> None:
    from src.common.exceptions import BadRequestException

    with pytest.raises(BadRequestException, match="PDF"):
        await service.detect_upload(filename="fake.pdf", content=b"not a pdf")


@pytest.mark.unit
async def test_detect_sample(service: DocumentService) -> None:
    result = await service.detect_sample("fiscal-page")
    assert "재정운영" in result.filename or result.filename.endswith(".png")
    assert result.page_count == 1
    assert result.blocks == []
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
