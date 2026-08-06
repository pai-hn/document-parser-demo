"""PyMuPDF 네이티브 텍스트 Extraction + 선택적 OCR 보강.

디지털 PDF는 get_text로 bbox/텍스트를 빠르게 뽑고,
글자가 거의 없는(스캔) 페이지는 OCR로 채운다.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import fitz

from src.document.domains import BBox, DetectionBlock

logger = logging.getLogger(__name__)

SOURCE_PDF_NAME = "source.pdf"
# 이보다 글자 수가 적으면 스캔/이미지 페이지로 보고 OCR 보강
_MIN_NATIVE_CHARS = 40


def _norm_rect(x0: float, y0: float, x1: float, y1: float, *, page_w: float, page_h: float) -> BBox | None:
    if page_w <= 0 or page_h <= 0:
        return None
    box = BBox.from_xyxy(x0 / page_w, y0 / page_h, x1 / page_w, y1 / page_h)
    if box.w <= 0.001 or box.h <= 0.001:
        return None
    return box


def _classify_text_block(text: str, bbox: BBox) -> str:
    """단순 규칙으로 text / marginalia 분류."""
    stripped = text.strip()
    if not stripped:
        return "text"
    # 페이지 번호·하단 꼬리표
    if bbox.y >= 0.88 or bbox.y + bbox.h <= 0.08:
        if len(stripped) <= 40 or re.fullmatch(r"\d{1,4}", stripped):
            return "marginalia"
    if re.fullmatch(r"\d{1,4}", stripped) and bbox.w < 0.15 and bbox.h < 0.05:
        return "marginalia"
    return "text"


def extract_native_blocks(
    *,
    pdf_path: Path,
    page_number: int,
    start_index: int,
) -> tuple[list[DetectionBlock], int]:
    """PDF 한 페이지에서 네이티브 텍스트/표 블록을 추출한다.

    Returns:
        (blocks, char_count)
    """
    doc = fitz.open(pdf_path)
    try:
        if page_number < 1 or page_number > doc.page_count:
            return [], 0
        page = doc.load_page(page_number - 1)
        page_w = float(page.rect.width)
        page_h = float(page.rect.height)
        blocks: list[DetectionBlock] = []
        index = start_index
        char_count = 0

        # 표 먼저 (있으면)
        try:
            finder = page.find_tables()
            tables = list(finder.tables) if finder is not None else []
        except Exception:  # noqa: BLE001
            tables = []

        table_rects: list[fitz.Rect] = []
        for table in tables:
            try:
                bbox_t = table.bbox  # type: ignore[attr-defined]
                rect = fitz.Rect(bbox_t)
            except Exception:  # noqa: BLE001
                continue
            table_rects.append(rect)
            box = _norm_rect(rect.x0, rect.y0, rect.x1, rect.y1, page_w=page_w, page_h=page_h)
            if box is None:
                continue
            try:
                md = table.to_markdown()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                md = "(table)"
            md = (md or "").strip() or "(table)"
            char_count += len(re.sub(r"\s+", "", md))
            html = ""
            try:
                df = table.to_pandas()  # type: ignore[attr-defined]
                html = df.to_html(index=False)
            except Exception:  # noqa: BLE001
                html = ""
            blocks.append(
                DetectionBlock(
                    id=str(index),
                    index=index,
                    page=page_number,
                    type="table",
                    bbox=box,
                    markdown=md if not html else f"{md}\n\n{html}",
                    html=html,
                )
            )
            index += 1

        def _overlaps_table(x0: float, y0: float, x1: float, y1: float) -> bool:
            r = fitz.Rect(x0, y0, x1, y1)
            for tr in table_rects:
                inter = r & tr
                if inter.is_empty:
                    continue
                if inter.get_area() / max(r.get_area(), 1e-6) > 0.5:
                    return True
            return False

        data = page.get_text("dict")
        for block in data.get("blocks", []):
            if block.get("type") != 0:  # 0 = text
                continue
            lines_text: list[str] = []
            x0 = y0 = float("inf")
            x1 = y1 = float("-inf")
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_parts = [str(s.get("text", "")) for s in spans if str(s.get("text", "")).strip()]
                if not line_parts:
                    continue
                lines_text.append("".join(line_parts).strip())
                for s in spans:
                    sb = s.get("bbox")
                    if not sb or len(sb) < 4:
                        continue
                    x0 = min(x0, float(sb[0]))
                    y0 = min(y0, float(sb[1]))
                    x1 = max(x1, float(sb[2]))
                    y1 = max(y1, float(sb[3]))
            text = "\n".join(t for t in lines_text if t).strip()
            if not text or x0 == float("inf"):
                continue
            if _overlaps_table(x0, y0, x1, y1):
                continue
            box = _norm_rect(x0, y0, x1, y1, page_w=page_w, page_h=page_h)
            if box is None:
                continue
            char_count += len(re.sub(r"\s+", "", text))
            btype = _classify_text_block(text, box)
            blocks.append(
                DetectionBlock(
                    id=str(index),
                    index=index,
                    page=page_number,
                    type=btype,  # type: ignore[arg-type]
                    bbox=box,
                    markdown=text,
                )
            )
            index += 1

        blocks.sort(key=lambda b: (b.bbox.y, b.bbox.x))
        for i, block in enumerate(blocks, start=start_index):
            block.id = str(i)
            block.index = i
        return blocks, char_count
    finally:
        doc.close()


class PymupdfNativeEngine:
    """PyMuPDF 네이티브 텍스트 (+ 선택 OCR)."""

    def __init__(self, *, ocr_lang: str = "korean") -> None:
        self._ocr_lang = ocr_lang
        self._ocr = None
        self._ocr_failed = False

    def _ensure_ocr(self):
        if self._ocr is not None or self._ocr_failed:
            return self._ocr
        try:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self._ocr_lang if self._ocr_lang in {"korean", "en", "ch"} else "korean",
                show_log=False,
            )
            logger.info("PyMuPDF OCR helper ready (lang=%s)", self._ocr_lang)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to init OCR helper for PyMuPDF pipeline", exc_info=True)
            self._ocr_failed = True
            self._ocr = None
        return self._ocr

    def _ocr_image_blocks(
        self,
        *,
        image_path: Path,
        page_number: int,
        start_index: int,
        width: int,
        height: int,
    ) -> list[DetectionBlock]:
        ocr = self._ensure_ocr()
        if ocr is None:
            return []
        try:
            result = ocr.ocr(str(image_path), cls=True)
        except Exception:  # noqa: BLE001
            logger.exception("OCR failed for %s", image_path)
            return []
        if not result:
            return []
        page = result[0] if isinstance(result, list) else result
        if not page:
            return []

        w = max(width, 1)
        h = max(height, 1)
        blocks: list[DetectionBlock] = []
        index = start_index
        for item in page:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            box_pts, payload = item[0], item[1]
            if not isinstance(payload, (list, tuple)) or not payload:
                continue
            text = str(payload[0]).strip()
            if not text or not box_pts:
                continue
            xs = [float(p[0]) for p in box_pts]
            ys = [float(p[1]) for p in box_pts]
            bbox = BBox.from_xyxy(min(xs) / w, min(ys) / h, max(xs) / w, max(ys) / h)
            if bbox.w <= 0.001 or bbox.h <= 0.001:
                continue
            btype = _classify_text_block(text, bbox)
            blocks.append(
                DetectionBlock(
                    id=str(index),
                    index=index,
                    page=page_number,
                    type=btype,  # type: ignore[arg-type]
                    bbox=bbox,
                    markdown=text,
                )
            )
            index += 1

        blocks.sort(key=lambda b: (b.bbox.y, b.bbox.x))
        for i, block in enumerate(blocks, start=start_index):
            block.id = str(i)
            block.index = i
        return blocks

    def detect_page(
        self,
        *,
        image_path: Path,
        page_number: int,
        start_index: int,
        width: int,
        height: int,
        enable_ocr: bool = False,
    ) -> list[DetectionBlock]:
        """페이지 Detection. source.pdf가 있으면 네이티브 텍스트 우선."""
        pdf_path = image_path.parent / SOURCE_PDF_NAME
        blocks: list[DetectionBlock] = []
        char_count = 0

        if pdf_path.is_file():
            try:
                blocks, char_count = extract_native_blocks(
                    pdf_path=pdf_path,
                    page_number=page_number,
                    start_index=start_index,
                )
            except Exception:  # noqa: BLE001
                logger.exception("Native PyMuPDF extract failed page=%s", page_number)
                blocks, char_count = [], 0

        needs_ocr = enable_ocr and (char_count < _MIN_NATIVE_CHARS or not blocks)
        if needs_ocr:
            logger.info(
                "PyMuPDF OCR fallback page=%s chars=%s blocks=%s",
                page_number,
                char_count,
                len(blocks),
            )
            ocr_blocks = self._ocr_image_blocks(
                image_path=image_path,
                page_number=page_number,
                start_index=start_index,
                width=width,
                height=height,
            )
            if ocr_blocks:
                return ocr_blocks

        return blocks


__all__ = ["PymupdfNativeEngine", "SOURCE_PDF_NAME", "extract_native_blocks"]
