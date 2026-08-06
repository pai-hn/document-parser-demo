"""PyMuPDF 기반 PDF 레이아웃 Detection 서비스."""

from __future__ import annotations

import logging
import struct
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from uuid import UUID

import fitz

from src.common.exceptions import BadRequestException, NotFoundException
from src.document.domains import (
    BBox,
    BlockType,
    DetectionBlock,
    DetectionResult,
    DocumentPage,
    SampleProject,
)
from src.utils import new_uuid

logger = logging.getLogger(__name__)

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parents[2] / ".data" / "uploads"

PDF_SUFFIXES = {".pdf"}
# 데모 안전을 위한 상한 (Landing AI류 장문 PDF도 처리하되 과도한 렌더는 제한)
MAX_PDF_PAGES = 200

SAMPLE_PROJECTS: list[SampleProject] = [
    SampleProject(
        sample_id="fiscal-page",
        title="3. 2026년 지방세 안내책 - 재정운영",
        file_count=1,
        filename="fiscal-page.png",
    ),
    SampleProject(
        sample_id="tax-guide",
        title="3. 2026년 지방세 안내책",
        file_count=1,
        filename="tax-guide.png",
    ),
]


def _normalized_bbox(rect: fitz.Rect, page_rect: fitz.Rect) -> BBox:
    """페이지 좌표 bbox를 0–1 범위로 정규화한다."""
    clipped = rect & page_rect
    return BBox(
        x=max(0.0, min(1.0, clipped.x0 / page_rect.width)),
        y=max(0.0, min(1.0, clipped.y0 / page_rect.height)),
        w=max(0.0, min(1.0, clipped.width / page_rect.width)),
        h=max(0.0, min(1.0, clipped.height / page_rect.height)),
    )


def _overlap_ratio(rect: fitz.Rect, regions: Iterable[fitz.Rect]) -> float:
    """rect 면적 중 다른 영역과 겹치는 최대 비율을 반환한다."""
    if rect.is_empty or rect.get_area() <= 0:
        return 0.0
    return max(((rect & region).get_area() / rect.get_area() for region in regions), default=0.0)


def _text_from_block(block: dict[str, Any]) -> str:
    """PyMuPDF text block에서 줄바꿈을 보존한 텍스트를 추출한다."""
    lines: list[str] = []
    for line in block.get("lines", []):
        text = "".join(str(span.get("text", "")) for span in line.get("spans", [])).strip()
        if text:
            lines.append(text)
    return "\n".join(lines).strip()


def _table_markdown(rows: list[list[str | None]]) -> str:
    """PyMuPDF 표 추출 결과를 Markdown 표로 변환한다."""
    if not rows:
        return "| 표 |\n| --- |"

    width = max(len(row) for row in rows)

    def clean(value: str | None) -> str:
        return (value or "").replace("|", "\\|").replace("\n", "<br>").strip()

    normalized = [[clean(row[index] if index < len(row) else None) for index in range(width)] for row in rows]
    header = normalized[0]
    body = normalized[1:]
    return "\n".join(
        [
            f"| {' | '.join(header)} |",
            f"| {' | '.join('---' for _ in range(width))} |",
            *(f"| {' | '.join(row)} |" for row in body),
        ]
    )


def _detect_page_elements(page: fitz.Page, *, page_number: int) -> list[tuple[BlockType, BBox, str]]:
    """페이지의 표·이미지·텍스트·여백 요소를 휴리스틱으로 검출한다."""
    page_rect = page.rect
    detected: list[tuple[BlockType, fitz.Rect, str]] = []
    occupied: list[fitz.Rect] = []

    try:
        tables = page.find_tables().tables
    except Exception:  # noqa: BLE001 - 일부 손상 페이지는 표 탐지만 실패할 수 있다.
        logger.warning("Table detection failed on page %s", page_number, exc_info=True)
        tables = []

    for table in tables:
        rect = fitz.Rect(table.bbox) & page_rect
        if rect.is_empty:
            continue
        detected.append(("table", rect, _table_markdown(table.extract())))
        occupied.append(rect)

    raw = page.get_text("dict", sort=True)
    for block in raw.get("blocks", []):
        if block.get("type") != 1 or "bbox" not in block:
            continue
        rect = fitz.Rect(block["bbox"]) & page_rect
        if rect.is_empty or _overlap_ratio(rect, occupied) > 0.6:
            continue
        detected.append(("figure", rect, f"![페이지 {page_number} 이미지](figure-{page_number})"))
        occupied.append(rect)

    for block in raw.get("blocks", []):
        if block.get("type") != 0 or "bbox" not in block:
            continue
        text = _text_from_block(block)
        if not text:
            continue
        rect = fitz.Rect(block["bbox"]) & page_rect
        if rect.is_empty or _overlap_ratio(rect, occupied) > 0.65:
            continue
        normalized_y = rect.y0 / page_rect.height
        normalized_bottom = rect.y1 / page_rect.height
        element_type: BlockType = (
            "marginalia" if normalized_y <= 0.07 or normalized_bottom >= 0.93 else "text"
        )
        detected.append((element_type, rect, text))

    detected.sort(key=lambda item: (round(item[1].y0, 1), round(item[1].x0, 1), item[0]))
    return [(element_type, _normalized_bbox(rect, page_rect), markdown) for element_type, rect, markdown in detected]


def _read_image_size(path: Path) -> tuple[int, int]:
    """PNG/JPEG 헤더에서 가로·세로를 읽는다. 실패 시 기본값을 반환한다."""
    try:
        data = path.read_bytes()
    except OSError:
        return 900, 1200

    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)

    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                break
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                height, width = struct.unpack(">HH", data[i + 5 : i + 9])
                return int(width), int(height)
            length = struct.unpack(">H", data[i + 2 : i + 4])[0]
            i += 2 + length

    return 900, 1200


def _render_pdf_pages(content: bytes, page_dir: Path) -> list[tuple[int, Path, int, int]]:
    """PDF 모든 페이지를 PNG로 렌더링한다.

    Returns:
        (page_number, image_path, width, height) 목록 (1-based page_number).
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise BadRequestException("PDF를 열 수 없습니다. 파일이 손상되었는지 확인해 주세요.") from exc

    if doc.page_count < 1:
        doc.close()
        raise BadRequestException("PDF에 페이지가 없습니다.")

    page_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[tuple[int, Path, int, int]] = []

    try:
        total = min(doc.page_count, MAX_PDF_PAGES)
        if doc.page_count > MAX_PDF_PAGES:
            logger.warning("PDF has %s pages; rendering first %s only", doc.page_count, MAX_PDF_PAGES)

        matrix = fitz.Matrix(2, 2)
        for i in range(total):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            page_number = i + 1
            image_path = page_dir / f"page-{page_number:04d}.png"
            image_path.write_bytes(pix.tobytes("png"))
            rendered.append((page_number, image_path, int(pix.width), int(pix.height)))
    finally:
        doc.close()

    return rendered


def _detect_pdf_elements(content: bytes) -> dict[int, list[tuple[BlockType, BBox, str]]]:
    """PDF 전체 페이지의 레이아웃 요소를 검출한다."""
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise BadRequestException("PDF를 열 수 없습니다. 파일이 손상되었는지 확인해 주세요.") from exc

    detected: dict[int, list[tuple[BlockType, BBox, str]]] = {}
    try:
        for index in range(min(doc.page_count, MAX_PDF_PAGES)):
            page_number = index + 1
            detected[page_number] = _detect_page_elements(doc.load_page(index), page_number=page_number)
    finally:
        doc.close()
    return detected


def _build_pages_from_images(
    *,
    image_entries: list[tuple[int, Path, int, int]],
    elements_by_page: dict[int, list[tuple[BlockType, BBox, str]]] | None = None,
) -> list[DocumentPage]:
    """렌더링 이미지와 검출 요소를 DocumentPage 목록으로 변환한다."""
    pages: list[DocumentPage] = []
    next_index = 1
    for page_number, image_path, width, height in image_entries:
        elements = (elements_by_page or {}).get(page_number, [])
        blocks = [
            DetectionBlock(
                id=str(next_index + offset),
                index=next_index + offset,
                page=page_number,
                type=element_type,
                bbox=bbox,
                markdown=markdown,
            )
            for offset, (element_type, bbox, markdown) in enumerate(elements)
        ]
        next_index += len(blocks)
        pages.append(
            DocumentPage(
                page_number=page_number,
                width=width,
                height=height,
                image_path=str(image_path),
                blocks=blocks,
            )
        )
    return pages


def _materialize_pages(*, document_id: UUID, filename: str, content: bytes, upload_dir: Path) -> list[DocumentPage]:
    """업로드 바이트를 페이지별 PNG로 저장하고 DocumentPage 목록을 반환한다."""
    suffix = Path(filename).suffix.lower()
    page_dir = upload_dir / str(document_id)

    if suffix not in PDF_SUFFIXES or content[:4] != b"%PDF":
        raise BadRequestException(
            "PDF 파일만 업로드할 수 있습니다.",
            detail={"filename": filename},
        )

    rendered = _render_pdf_pages(content, page_dir)
    detected = _detect_pdf_elements(content)
    return _build_pages_from_images(image_entries=rendered, elements_by_page=detected)


class DocumentService:
    """문서 업로드·Detection stub 서비스."""

    def __init__(self, upload_dir: Path | None = None) -> None:
        self._upload_dir = upload_dir or DEFAULT_UPLOAD_DIR
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._results: dict[UUID, DetectionResult] = {}

    def list_samples(self) -> list[SampleProject]:
        """사용 가능한 샘플 프로젝트 목록을 반환한다."""
        return list(SAMPLE_PROJECTS)

    def get_sample(self, sample_id: str) -> SampleProject:
        """샘플 메타데이터를 조회한다."""
        for sample in SAMPLE_PROJECTS:
            if sample.sample_id == sample_id:
                return sample
        raise NotFoundException(f"Sample '{sample_id}' not found")

    async def detect_upload(self, *, filename: str, content: bytes) -> DetectionResult:
        """업로드 파일을 저장하고 전체 페이지 Detection 결과를 반환한다."""
        if not content:
            raise BadRequestException("빈 파일은 업로드할 수 없습니다.")

        document_id = new_uuid()
        pages = _materialize_pages(
            document_id=document_id,
            filename=filename,
            content=content,
            upload_dir=self._upload_dir,
        )
        result = DetectionResult(document_id=document_id, filename=filename, pages=pages)
        self._results[document_id] = result
        logger.info(
            "Detected upload document_id=%s filename=%s pages=%s",
            document_id,
            filename,
            result.page_count,
        )
        return result

    async def detect_sample(self, sample_id: str) -> DetectionResult:
        """샘플 이미지에 대해 stub Detection을 수행한다."""
        sample = self.get_sample(sample_id)
        source = SAMPLES_DIR / sample.filename
        if not source.is_file():
            raise NotFoundException(f"Sample file missing: {sample.filename}")

        document_id = new_uuid()
        page_dir = self._upload_dir / str(document_id)
        page_dir.mkdir(parents=True, exist_ok=True)
        dest = page_dir / f"page-0001{source.suffix}"
        dest.write_bytes(source.read_bytes())
        width, height = _read_image_size(dest)
        pages = _build_pages_from_images(
            image_entries=[(1, dest, width, height)],
        )
        result = DetectionResult(
            document_id=document_id,
            filename=sample.title + source.suffix,
            pages=pages,
        )
        self._results[document_id] = result
        return result

    async def get_document(self, document_id: UUID) -> DetectionResult:
        """저장된 Detection 결과를 조회한다."""
        result = self._results.get(document_id)
        if result is None:
            raise NotFoundException(f"Document '{document_id}' not found")
        return result

    async def get_page_image_path(self, document_id: UUID, page_number: int) -> Path:
        """문서의 특정 페이지 이미지 경로를 반환한다."""
        result = await self.get_document(document_id)
        try:
            page = result.get_page(page_number)
        except KeyError as exc:
            raise NotFoundException(f"Page {page_number} not found") from exc
        path = Path(page.image_path)
        if not path.is_file():
            raise NotFoundException("Document page image file is missing")
        return path

    async def get_image_path(self, document_id: UUID) -> Path:
        """첫 페이지 이미지 경로를 반환한다 (하위 호환)."""
        return await self.get_page_image_path(document_id, 1)
