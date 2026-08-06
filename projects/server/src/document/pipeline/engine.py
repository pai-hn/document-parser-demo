"""Detection 파이프라인 파사드 (Paddle / Vision / PyMuPDF)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from src.document.domains import DetectionBlock
from src.document.pipeline.docling_engine import DoclingEngine
from src.document.pipeline.llm_refiner import LlmMarkdownRefiner
from src.document.pipeline.pymupdf_engine import PymupdfNativeEngine
from src.document.pipeline.vision_llm_engine import VisionLlmEngine, normalize_engine_name
from src.document.settings import DocumentSettings

logger = logging.getLogger(__name__)


class LayoutOcrPipeline:
    """페이지 이미지 → DetectionBlock 목록."""

    def __init__(self, settings: DocumentSettings | None = None) -> None:
        self._settings = settings or DocumentSettings()
        self._paddle = None
        self._vision = VisionLlmEngine(self._settings)
        self._pymupdf = PymupdfNativeEngine(ocr_lang=self._settings.document_ocr_lang)
        self._docling = DoclingEngine()
        self._refiner = LlmMarkdownRefiner(self._settings)
        self._init_error: str | None = None
        self._paddle_initialized = False

    @property
    def docling(self) -> DoclingEngine:
        """Docling 엔진 (문서 단위 변환용)."""
        return self._docling

    @property
    def available(self) -> bool:
        """사용 가능한 엔진이 하나라도 있으면 True."""
        return True

    @property
    def init_error(self) -> str | None:
        self._ensure_paddle()
        return self._init_error

    def _ensure_paddle(self):
        if self._paddle_initialized:
            return self._paddle
        self._paddle_initialized = True
        try:
            from src.document.pipeline.paddle_engine import PaddleLayoutOcrEngine

            self._paddle = PaddleLayoutOcrEngine(ocr_lang=self._settings.document_ocr_lang)
        except Exception as exc:  # noqa: BLE001
            self._init_error = str(exc)
            logger.exception("Failed to initialize layout OCR engine")
            self._paddle = None
        return self._paddle

    async def detect_page(
        self,
        *,
        image_path: Path,
        page_number: int,
        start_index: int,
        width: int,
        height: int,
        engine: str | None = None,
    ) -> list[DetectionBlock]:
        """한 페이지를 Detection한다.

        engine:
          - paddle / paddle_llm
          - vision_llm
          - pymupdf / pymupdf_ocr
          - docling (문서는 service에서 일괄 변환 권장)
        """
        mode = normalize_engine_name(engine or self._settings.document_detection_engine)

        if mode == "docling":
            # 페이지 단위 호출 시 해당 이미지만 변환 (느림). PDF는 service 일괄 경로 사용.
            by_page = await asyncio.to_thread(
                self._docling.convert_file,
                image_path,
                start_index=start_index,
            )
            return by_page.get(1) or by_page.get(page_number) or []

        if mode in {"pymupdf", "pymupdf_ocr"}:
            return await asyncio.to_thread(
                self._pymupdf.detect_page,
                image_path=image_path,
                page_number=page_number,
                start_index=start_index,
                width=width,
                height=height,
                enable_ocr=(mode == "pymupdf_ocr"),
            )

        if mode == "vision_llm":
            if not self._vision.configured:
                self._init_error = "Vision LLM requires DOCUMENT_LLM_API_KEY"
                return []
            return await self._vision.detect_page(
                image_path=image_path,
                page_number=page_number,
                start_index=start_index,
                width=width,
                height=height,
            )

        paddle = self._ensure_paddle()
        if paddle is None:
            return []

        blocks = await asyncio.to_thread(
            paddle.detect_page,
            image_path=image_path,
            page_number=page_number,
            start_index=start_index,
            width=width,
            height=height,
        )
        if mode == "paddle_llm" and page_number <= 3:
            return await self._refiner.refine_blocks(blocks, force=True)
        return blocks
