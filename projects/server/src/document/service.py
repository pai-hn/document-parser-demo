"""Document Detection 서비스.

PDF/이미지를 페이지 PNG로 렌더한 뒤 Layout+OCR(+LLM) 파이프라인으로
실제 Detection 블록을 생성한다. 엔진 실패 시 stub로 폴백할 수 있다.
"""

from __future__ import annotations

import asyncio
import json
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
from src.document.pipeline.engine import LayoutOcrPipeline
from src.document.pipeline.pymupdf_engine import SOURCE_PDF_NAME
from src.document.pipeline.vision_llm_engine import normalize_engine_name
from src.document.settings import DocumentSettings
from src.utils import new_uuid

logger = logging.getLogger(__name__)

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parents[2] / ".data" / "uploads"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
PDF_SUFFIXES = {".pdf"}
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
    """엔진 실패 시 사용하는 stub 박스."""
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
    """PNG/JPEG 헤더에서 가로·세로를 읽는다."""
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
    """PDF 모든 페이지를 PNG로 렌더링한다."""
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


def _materialize_images(
    *, document_id: UUID, filename: str, content: bytes, upload_dir: Path
) -> list[tuple[int, Path, int, int]]:
    """업로드를 페이지 이미지 목록으로 저장한다."""
    suffix = Path(filename).suffix.lower()
    page_dir = upload_dir / str(document_id)

    if suffix in PDF_SUFFIXES or content[:4] == b"%PDF":
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / SOURCE_PDF_NAME).write_bytes(content)
        return _render_pdf_pages(content, page_dir)

    if suffix in IMAGE_SUFFIXES or content[:8] == b"\x89PNG\r\n\x1a\n" or content[:2] == b"\xff\xd8":
        ext = suffix if suffix in IMAGE_SUFFIXES else ".png"
        if content[:2] == b"\xff\xd8" and ext not in {".jpg", ".jpeg"}:
            ext = ".jpg"
        page_dir.mkdir(parents=True, exist_ok=True)
        image_path = page_dir / f"page-0001{ext}"
        image_path.write_bytes(content)
        width, height = _read_image_size(image_path)
        return [(1, image_path, width, height)]

    raise BadRequestException(
        "지원하지 않는 파일 형식입니다. PNG, JPG, WEBP, PDF만 업로드할 수 있습니다.",
        detail={"filename": filename},
    )


def _result_to_dict(result: DetectionResult) -> dict:
    """DetectionResult를 JSON 직렬화 가능한 dict로 변환한다."""
    return {
        "document_id": str(result.document_id),
        "filename": result.filename,
        "pages": [
            {
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "image_path": page.image_path,
                "blocks": [
                    {
                        "id": block.id,
                        "index": block.index,
                        "page": block.page,
                        "type": block.type,
                        "bbox": {
                            "x": block.bbox.x,
                            "y": block.bbox.y,
                            "w": block.bbox.w,
                            "h": block.bbox.h,
                        },
                        "markdown": block.markdown,
                        "html": getattr(block, "html", "") or "",
                    }
                    for block in page.blocks
                ],
            }
            for page in result.pages
        ],
    }


_LEGACY_TYPE_MAP: dict[str, BlockType] = {
    "heading": "text",
    "paragraph": "text",
    "caption": "text",
    "header": "text",
    "footer": "marginalia",
}


def _normalize_block_type(raw: str) -> BlockType:
    key = (raw or "text").strip().lower()
    mapped = _LEGACY_TYPE_MAP.get(key, key)
    if mapped in {"text", "figure", "table", "marginalia", "logo"}:
        return mapped  # type: ignore[return-value]
    return "text"


def _result_from_dict(data: dict) -> DetectionResult:
    """JSON dict를 DetectionResult로 복원한다."""
    pages: list[DocumentPage] = []
    for page in data.get("pages", []):
        blocks = [
            DetectionBlock(
                id=str(block["id"]),
                index=int(block["index"]),
                page=int(block["page"]),
                type=_normalize_block_type(str(block["type"])),
                bbox=BBox(
                    x=float(block["bbox"]["x"]),
                    y=float(block["bbox"]["y"]),
                    w=float(block["bbox"]["w"]),
                    h=float(block["bbox"]["h"]),
                ),
                markdown=str(block.get("markdown", "")),
                html=str(block.get("html", "")),
            )
            for block in page.get("blocks", [])
        ]
        pages.append(
            DocumentPage(
                page_number=int(page["page_number"]),
                width=int(page["width"]),
                height=int(page["height"]),
                image_path=str(page["image_path"]),
                blocks=blocks,
            )
        )
    return DetectionResult(
        document_id=UUID(str(data["document_id"])),
        filename=str(data["filename"]),
        pages=pages,
    )


class DocumentService:
    """문서 업로드·Layout+OCR Detection 서비스."""

    def __init__(
        self,
        upload_dir: Path | None = None,
        pipeline: LayoutOcrPipeline | None = None,
        settings: DocumentSettings | None = None,
    ) -> None:
        self._upload_dir = upload_dir or DEFAULT_UPLOAD_DIR
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._settings = settings or DocumentSettings()
        self._pipeline = pipeline or LayoutOcrPipeline(self._settings)
        self._results: dict[UUID, DetectionResult] = {}

    def _meta_path(self, document_id: UUID) -> Path:
        return self._upload_dir / str(document_id) / "result.json"

    def _save_result(self, result: DetectionResult) -> None:
        path = self._meta_path(result.document_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_result_to_dict(result), ensure_ascii=False), encoding="utf-8")

    def _load_result(self, document_id: UUID) -> DetectionResult | None:
        path = self._meta_path(document_id)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return _result_from_dict(data)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load persisted result %s", document_id)
            return None

    def list_samples(self) -> list[SampleProject]:
        """사용 가능한 샘플 프로젝트 목록을 반환한다."""
        return list(SAMPLE_PROJECTS)

    def get_sample(self, sample_id: str) -> SampleProject:
        """샘플 메타데이터를 조회한다."""
        for sample in SAMPLE_PROJECTS:
            if sample.sample_id == sample_id:
                return sample
        raise NotFoundException(f"Sample '{sample_id}' not found")

    async def _detect_pages(
        self,
        *,
        image_entries: list[tuple[int, Path, int, int]],
        stub_variant: str = "default",
        engine: str = "paddle",
    ) -> list[DocumentPage]:
        """페이지 이미지들에 대해 Detection을 수행한다."""
        mode = normalize_engine_name(engine)
        pages: list[DocumentPage] = []
        next_index = 1
        # Vision/PyMuPDF는 stub로 위장하면 안 됨
        use_stub = self._settings.document_use_stub_fallback and mode not in {
            "vision_llm",
            "pymupdf",
            "pymupdf_ocr",
            "docling",
        }

        if mode == "docling":
            return await self._detect_with_docling(image_entries=image_entries)

        for page_number, image_path, width, height in image_entries:
            blocks: list[DetectionBlock] = []
            try:
                blocks = await self._pipeline.detect_page(
                    image_path=image_path,
                    page_number=page_number,
                    start_index=next_index,
                    width=width,
                    height=height,
                    engine=mode,
                )
            except Exception:  # noqa: BLE001
                logger.exception("Detection failed for page %s mode=%s", page_number, mode)
                blocks = []

            if not blocks:
                if use_stub:
                    logger.warning(
                        "Using stub blocks for page %s (engine_available=%s error=%s)",
                        page_number,
                        self._pipeline.available,
                        self._pipeline.init_error,
                    )
                    blocks = _stub_blocks_for_page(
                        page_number=page_number,
                        start_index=next_index,
                        variant=stub_variant,
                    )
                else:
                    blocks = []

            next_index = (blocks[-1].index + 1) if blocks else next_index
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

    async def _detect_with_docling(
        self,
        *,
        image_entries: list[tuple[int, Path, int, int]],
    ) -> list[DocumentPage]:
        """Docling으로 문서를 한 번 변환해 페이지별 블록을 채운다."""
        if not image_entries:
            return []

        source = image_entries[0][1].parent / SOURCE_PDF_NAME
        if not source.is_file():
            # 샘플 PNG 등: 이미지들을 순서대로 변환해 합친다
            pages: list[DocumentPage] = []
            next_index = 1
            for page_number, image_path, width, height in image_entries:
                by_page = await asyncio.to_thread(
                    self._pipeline.docling.convert_file,
                    image_path,
                    start_index=next_index,
                )
                blocks = by_page.get(1) or next(iter(by_page.values()), [])
                for i, block in enumerate(blocks, start=next_index):
                    block.id = str(i)
                    block.index = i
                    block.page = page_number
                next_index = (blocks[-1].index + 1) if blocks else next_index
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

        by_page = await asyncio.to_thread(
            self._pipeline.docling.convert_file,
            source,
            start_index=1,
        )
        pages = []
        next_index = 1
        for page_number, image_path, width, height in image_entries:
            blocks = list(by_page.get(page_number, []))
            for i, block in enumerate(blocks, start=next_index):
                block.id = str(i)
                block.index = i
                block.page = page_number
            next_index = (blocks[-1].index + 1) if blocks else next_index
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

    async def detect_upload(
        self,
        *,
        filename: str,
        content: bytes,
        engine: str = "paddle",
    ) -> DetectionResult:
        """업로드 파일을 저장하고 Detection 결과를 반환한다."""
        if not content:
            raise BadRequestException("빈 파일은 업로드할 수 없습니다.")

        mode = normalize_engine_name(engine)
        document_id = new_uuid()
        image_entries = _materialize_images(
            document_id=document_id,
            filename=filename,
            content=content,
            upload_dir=self._upload_dir,
        )
        if mode == "vision_llm":
            max_pages = max(1, int(self._settings.document_vision_max_pages))
            if len(image_entries) > max_pages:
                logger.info(
                    "Vision LLM: limiting pages %s → %s",
                    len(image_entries),
                    max_pages,
                )
                image_entries = image_entries[:max_pages]

        pages = await self._detect_pages(
            image_entries=image_entries,
            stub_variant="default",
            engine=mode,
        )
        result = DetectionResult(document_id=document_id, filename=filename, pages=pages)
        self._results[document_id] = result
        self._save_result(result)
        logger.info(
            "Detected upload document_id=%s filename=%s pages=%s blocks=%s engine=%s",
            document_id,
            filename,
            result.page_count,
            len(result.blocks),
            mode,
        )
        return result

    async def detect_sample(self, sample_id: str, *, engine: str = "paddle") -> DetectionResult:
        """샘플 이미지에 대해 Detection을 수행한다."""
        sample = self.get_sample(sample_id)
        source = SAMPLES_DIR / sample.filename
        if not source.is_file():
            raise NotFoundException(f"Sample file missing: {sample.filename}")

        mode = normalize_engine_name(engine)
        document_id = new_uuid()
        page_dir = self._upload_dir / str(document_id)
        page_dir.mkdir(parents=True, exist_ok=True)
        dest = page_dir / f"page-0001{source.suffix}"
        dest.write_bytes(source.read_bytes())
        width, height = _read_image_size(dest)
        variant = "tax-guide" if sample_id == "tax-guide" else "default"
        pages = await self._detect_pages(
            image_entries=[(1, dest, width, height)],
            stub_variant=variant,
            engine=mode,
        )
        result = DetectionResult(
            document_id=document_id,
            filename=sample.title + source.suffix,
            pages=pages,
        )
        self._results[document_id] = result
        self._save_result(result)
        return result

    async def get_document(self, document_id: UUID) -> DetectionResult:
        """저장된 Detection 결과를 조회한다 (메모리 → 디스크)."""
        result = self._results.get(document_id)
        if result is not None:
            return result
        loaded = self._load_result(document_id)
        if loaded is not None:
            self._results[document_id] = loaded
            return loaded
        raise NotFoundException(f"Document '{document_id}' not found")

    async def get_page_image_path(self, document_id: UUID, page_number: int) -> Path:
        """문서의 특정 페이지 이미지 경로를 반환한다."""
        result = await self.get_document(document_id)
        try:
            page = result.get_page(page_number)
        except KeyError as exc:
            raise NotFoundException(f"Page {page_number} not found") from exc
        path = Path(page.image_path)
        if not path.is_file():
            # 상대 경로로 저장된 경우 upload_dir 기준으로 재시도
            alt = self._upload_dir / str(document_id) / path.name
            if alt.is_file():
                return alt
            raise NotFoundException("Document page image file is missing")
        return path

    async def get_image_path(self, document_id: UUID) -> Path:
        """첫 페이지 이미지 경로를 반환한다 (하위 호환)."""
        return await self.get_page_image_path(document_id, 1)
