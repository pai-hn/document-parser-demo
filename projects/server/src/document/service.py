"""Document Detection 서비스.

실제 OCR 엔진 대신 stub layout을 반환한다.
PDF는 모든 페이지를 PNG로 렌더링한 뒤 페이지별로 서빙한다.
"""

from __future__ import annotations

import logging
import struct
from pathlib import Path
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

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
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


def _stub_blocks_for_page(*, page_number: int, start_index: int, variant: str = "default") -> list[DetectionBlock]:
    """페이지별 stub 바운딩 박스를 생성한다. index는 문서 전역 연속 번호."""
    templates: list[tuple[BlockType, BBox, str]]
    if variant == "tax-guide":
        templates = [
            ("text", BBox(0.08, 0.06, 0.55, 0.08), f"# Page {page_number} — 국세 주요 세목별 안내"),
            ("text", BBox(0.08, 0.16, 0.55, 0.1), f"{page_number}페이지 국세 납부·신고 안내입니다."),
            ("figure", BBox(0.62, 0.05, 0.3, 0.22), f"![page-{page_number}-figure](figure)"),
            (
                "table",
                BBox(0.08, 0.35, 0.84, 0.28),
                f"| 세목 | 설명 |\n| --- | --- |\n| 소득세 | {page_number}페이지 |\n| 법인세 | 법인 소득 |",
            ),
            ("marginalia", BBox(0.08, 0.92, 0.4, 0.035), f"{page_number} _ 2026 지방세 안내"),
        ]
    else:
        # 페이지마다 레이아웃을 살짝 다르게 해 스크롤 시 구분이 되게 한다.
        y_shift = 0.02 * ((page_number - 1) % 3)
        templates = [
            ("text", BBox(0.08, 0.05 + y_shift, 0.72, 0.045), f"# {page_number}. 문서 페이지 {page_number}"),
            (
                "text",
                BBox(0.08, 0.14 + y_shift, 0.84, 0.12),
                f"- 페이지 {page_number} stub 본문\n- Detection 데모용 텍스트 블록",
            ),
            ("figure", BBox(0.12, 0.38 + y_shift, 0.76, 0.18), f"![page-{page_number}-figure](figure)"),
            (
                "table",
                BBox(0.08, 0.62, 0.84, 0.18),
                f"| 항목 | 값 |\n| --- | --- |\n| 페이지 | {page_number} |\n| 상태 | detected |",
            ),
            ("marginalia", BBox(0.08, 0.93, 0.35, 0.03), f"{page_number} _ document footer"),
        ]

    blocks: list[DetectionBlock] = []
    for offset, (block_type, bbox, markdown) in enumerate(templates):
        index = start_index + offset
        blocks.append(
            DetectionBlock(
                id=str(index),
                index=index,
                page=page_number,
                type=block_type,
                bbox=bbox,
                markdown=markdown,
            )
        )
    return blocks


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


def _build_pages_from_images(
    *,
    image_entries: list[tuple[int, Path, int, int]],
    variant: str,
) -> list[DocumentPage]:
    """이미지 목록에 stub blocks를 붙여 DocumentPage 목록을 만든다."""
    pages: list[DocumentPage] = []
    next_index = 1
    for page_number, image_path, width, height in image_entries:
        blocks = _stub_blocks_for_page(page_number=page_number, start_index=next_index, variant=variant)
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

    if suffix in PDF_SUFFIXES or content[:4] == b"%PDF":
        rendered = _render_pdf_pages(content, page_dir)
        return _build_pages_from_images(image_entries=rendered, variant="default")

    if suffix in IMAGE_SUFFIXES or content[:8] == b"\x89PNG\r\n\x1a\n" or content[:2] == b"\xff\xd8":
        ext = suffix if suffix in IMAGE_SUFFIXES else ".png"
        if content[:2] == b"\xff\xd8" and ext not in {".jpg", ".jpeg"}:
            ext = ".jpg"
        page_dir.mkdir(parents=True, exist_ok=True)
        image_path = page_dir / f"page-0001{ext}"
        image_path.write_bytes(content)
        width, height = _read_image_size(image_path)
        return _build_pages_from_images(
            image_entries=[(1, image_path, width, height)],
            variant="default",
        )

    raise BadRequestException(
        "지원하지 않는 파일 형식입니다. PNG, JPG, WEBP, PDF만 업로드할 수 있습니다.",
        detail={"filename": filename},
    )


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
        variant = "tax-guide" if sample_id == "tax-guide" else "default"
        pages = _build_pages_from_images(
            image_entries=[(1, dest, width, height)],
            variant=variant,
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
