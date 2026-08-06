"""PaddleOCR PPStructure 기반 Layout + OCR 엔진."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import cv2
import numpy as np

from src.document.domains import BBox, DetectionBlock
from src.document.pipeline.label_map import map_label

logger = logging.getLogger(__name__)


def _normalize_bbox(x1: float, y1: float, x2: float, y2: float, *, width: int, height: int) -> BBox:
    """픽셀 좌표를 0–1 정규화 bbox로 변환한다."""
    w = max(width, 1)
    h = max(height, 1)
    left = max(0.0, min(float(x1), float(x2))) / w
    top = max(0.0, min(float(y1), float(y2))) / h
    right = min(1.0, max(float(x1), float(x2)) / w)
    bottom = min(1.0, max(float(y1), float(y2)) / h)
    return BBox(
        x=round(left, 4),
        y=round(top, 4),
        w=round(max(0.0, right - left), 4),
        h=round(max(0.0, bottom - top), 4),
    )


def _html_table_to_markdown(html: str) -> str:
    """간단한 HTML table → markdown 변환."""
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.I | re.S)
    md_rows: list[list[str]] = []
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.I | re.S)
        cleaned = [re.sub(r"<[^>]+>", "", c).strip().replace("\n", " ") for c in cells]
        if cleaned:
            md_rows.append(cleaned)
    if not md_rows:
        return html.strip()
    width = max(len(r) for r in md_rows)
    normalized = [r + [""] * (width - len(r)) for r in md_rows]
    header = normalized[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in normalized[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _extract_text_from_ocr_res(res: object) -> str:
    """PPStructure OCR 결과에서 텍스트를 추출한다."""
    if res is None:
        return ""
    if isinstance(res, str):
        return res.strip()
    if isinstance(res, dict):
        if "html" in res and isinstance(res["html"], str):
            return _html_table_to_markdown(res["html"])
        if "text" in res:
            return str(res["text"]).strip()
    if isinstance(res, list):
        lines: list[str] = []
        for item in res:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                second = item[1]
                if isinstance(second, (list, tuple)) and second:
                    lines.append(str(second[0]))
                else:
                    lines.append(str(second))
            elif isinstance(item, dict) and "text" in item:
                lines.append(str(item["text"]))
        return "\n".join(line for line in lines if line).strip()
    return str(res).strip()


class PaddleLayoutOcrEngine:
    """PPStructure(layout) + 한국어 OCR 보조."""

    def __init__(self, *, ocr_lang: str = "korean") -> None:
        self._ocr_lang = ocr_lang
        self._structure = None
        self._korean_ocr = None
        self._init_engines()

    def _init_engines(self) -> None:
        from paddleocr import PPStructure

        # layout 모델은 ch/en만 지원. OCR는 한국어를 별도로 시도한다.
        logger.info("Initializing PPStructure layout+ocr engine")
        self._structure = PPStructure(
            show_log=False,
            recovery=False,
            lang="ch",
            layout=True,
            table=True,
            ocr=True,
        )
        try:
            from paddleocr import PaddleOCR

            self._korean_ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self._ocr_lang if self._ocr_lang in {"korean", "en", "ch"} else "korean",
                show_log=False,
            )
            logger.info("Korean/aux OCR ready (lang=%s)", self._ocr_lang)
        except Exception:  # noqa: BLE001
            logger.warning("Aux OCR init failed; using PPStructure OCR text only", exc_info=True)
            self._korean_ocr = None

    def detect_page(
        self,
        *,
        image_path: Path,
        page_number: int,
        start_index: int,
        width: int,
        height: int,
    ) -> list[DetectionBlock]:
        """단일 페이지 이미지에서 DetectionBlock 목록을 생성한다."""
        if self._structure is None:
            raise RuntimeError("PPStructure engine is not initialized")

        image = cv2.imread(str(image_path))
        if image is None:
            raise RuntimeError(f"Failed to read image: {image_path}")

        img_h, img_w = image.shape[:2]
        width = width or img_w
        height = height or img_h

        regions = self._structure(image)
        blocks: list[DetectionBlock] = []
        index = start_index

        for region in regions:
            label = region.get("type")
            block_type = map_label(label if isinstance(label, str) else None)
            if block_type is None:
                continue

            bbox_raw = region.get("bbox") or region.get("coordinate")
            if not bbox_raw or len(bbox_raw) < 4:
                continue
            x1, y1, x2, y2 = (float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3]))
            bbox = _normalize_bbox(x1, y1, x2, y2, width=width, height=height)
            if bbox.w <= 0.001 or bbox.h <= 0.001:
                continue

            markdown = _extract_text_from_ocr_res(region.get("res"))
            if block_type in {"text", "marginalia"} and self._korean_ocr is not None:
                cropped = self._ocr_crop(image, x1, y1, x2, y2)
                if cropped:
                    markdown = cropped or markdown
            if block_type == "figure" and not markdown:
                markdown = f"![figure p{page_number}-{index}](figure)"
            if not markdown:
                markdown = f"({block_type})"

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
            index += 1

        # reading order: top-to-bottom, left-to-right
        blocks.sort(key=lambda b: (b.bbox.y, b.bbox.x))
        for i, block in enumerate(blocks, start=start_index):
            block.id = str(i)
            block.index = i
        return blocks

    def _ocr_crop(self, image: np.ndarray, x1: float, y1: float, x2: float, y2: float) -> str:
        """영역 crop 후 보조 OCR을 수행한다."""
        if self._korean_ocr is None:
            return ""
        h, w = image.shape[:2]
        left = max(0, int(min(x1, x2)))
        top = max(0, int(min(y1, y2)))
        right = min(w, int(max(x1, x2)))
        bottom = min(h, int(max(y1, y2)))
        if right - left < 2 or bottom - top < 2:
            return ""
        crop = image[top:bottom, left:right]
        try:
            result = self._korean_ocr.ocr(crop, cls=True)
        except Exception:  # noqa: BLE001
            logger.debug("crop OCR failed", exc_info=True)
            return ""
        if not result:
            return ""
        lines: list[str] = []
        # PaddleOCR returns [ [ [box, (text, conf)], ... ] ] or None
        page = result[0] if isinstance(result, list) and result else result
        if not page:
            return ""
        for item in page:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                second = item[1]
                if isinstance(second, (list, tuple)) and second:
                    lines.append(str(second[0]))
        return "\n".join(lines).strip()
