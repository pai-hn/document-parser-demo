"""DocumentService unit tests."""

from pathlib import Path

import pytest

from src.common.exceptions import NotFoundException
from src.document.service import DocumentService, _read_image_size, _stub_blocks_for_page


@pytest.fixture
def service(tmp_path: Path) -> DocumentService:
    return DocumentService(upload_dir=tmp_path)


@pytest.mark.unit
def test_stub_blocks_include_all_types() -> None:
    blocks = _stub_blocks_for_page(page_number=1, start_index=1, variant="default")
    types = {b.type for b in blocks}
    assert types == {"text", "figure", "table", "marginalia"}
    assert all(b.page == 1 for b in blocks)


@pytest.mark.unit
def test_list_samples(service: DocumentService) -> None:
    samples = service.list_samples()
    assert len(samples) >= 2
    assert {s.sample_id for s in samples} >= {"fiscal-page", "tax-guide"}


@pytest.mark.unit
async def test_detect_upload(service: DocumentService) -> None:
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    result = await service.detect_upload(filename="tiny.png", content=png)
    assert result.filename == "tiny.png"
    assert result.page_count == 1
    assert result.page_width == 1
    assert result.page_height == 1
    assert any(b.type == "table" for b in result.blocks)
    assert Path(result.pages[0].image_path).is_file()

    loaded = await service.get_document(result.document_id)
    assert loaded.document_id == result.document_id


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

    page2 = await service.get_page_image_path(result.document_id, 2)
    assert page2.is_file()


@pytest.mark.unit
async def test_detect_upload_rejects_unsupported(service: DocumentService) -> None:
    from src.common.exceptions import BadRequestException

    with pytest.raises(BadRequestException):
        await service.detect_upload(filename="note.docx", content=b"PK\x03\x04fake")


@pytest.mark.unit
async def test_detect_sample(service: DocumentService) -> None:
    result = await service.detect_sample("fiscal-page")
    assert "재정운영" in result.filename or result.filename.endswith(".png")
    assert result.page_count == 1
    assert len(result.blocks) >= 4
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
