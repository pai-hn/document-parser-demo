"""Docling Detection 엔진.

문서 전체를 한 번 변환한 뒤 page별 DetectionBlock으로 매핑한다.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.document.domains import BBox, BlockType, DetectionBlock

logger = logging.getLogger(__name__)

_LABEL_TO_TYPE: dict[str, BlockType] = {
    "text": "text",
    "paragraph": "text",
    "title": "text",
    "section_header": "text",
    "caption": "text",
    "list_item": "text",
    "code": "text",
    "formula": "text",
    "checkbox_selected": "text",
    "checkbox_unselected": "text",
    "document_index": "text",
    "reference": "text",
    "handwritten_text": "text",
    "key_value_region": "text",
    "form": "text",
    "table": "table",
    "picture": "figure",
    "chart": "figure",
    "page_header": "marginalia",
    "page_footer": "marginalia",
    "footnote": "marginalia",
}


def map_docling_label(label: object) -> BlockType | None:
    """Docling DocItemLabel → 도메인 BlockType."""
    if label is None:
        return None
    key = getattr(label, "value", None) or getattr(label, "name", None) or str(label)
    key = str(key).strip().lower()
    return _LABEL_TO_TYPE.get(key)


def _page_size(doc: Any, page_no: int) -> tuple[float, float]:
    page = None
    pages = getattr(doc, "pages", None)
    if isinstance(pages, dict):
        page = pages.get(page_no)
    if page is None and hasattr(doc, "pages"):
        try:
            page = doc.pages[page_no]
        except Exception:  # noqa: BLE001
            page = None
    if page is not None and getattr(page, "size", None) is not None:
        return float(page.size.width), float(page.size.height)
    return 1.0, 1.0


def _bbox_to_normalized(bbox: Any, *, page_w: float, page_h: float) -> BBox | None:
    if bbox is None or page_w <= 0 or page_h <= 0:
        return None
    try:
        # Docling은 기본 BOTTOMLEFT. 우리 UI는 top-left 정규화.
        if hasattr(bbox, "to_top_left_origin"):
            bbox = bbox.to_top_left_origin(page_height=page_h)
        l = float(bbox.l)
        t = float(bbox.t)
        r = float(bbox.r)
        b = float(bbox.b)
    except Exception:  # noqa: BLE001
        return None
    return BBox.from_xyxy(l / page_w, t / page_h, r / page_w, b / page_h)


def _element_markdown(element: Any, doc: Any) -> tuple[str, str]:
    """(markdown, html) 추출."""
    html = ""
    label = str(getattr(element, "label", "") or "").lower()
    text = str(getattr(element, "text", "") or "").strip()

    # Table
    if "table" in type(element).__name__.lower() or label.endswith("table"):
        md = ""
        try:
            md = element.export_to_markdown(doc=doc)  # type: ignore[call-arg]
        except Exception:  # noqa: BLE001
            try:
                md = element.export_to_markdown()
            except Exception:  # noqa: BLE001
                md = text
        try:
            html = element.export_to_html(doc=doc)  # type: ignore[call-arg]
        except Exception:  # noqa: BLE001
            try:
                html = element.export_to_html()
            except Exception:  # noqa: BLE001
                html = ""
        md = (md or text or "(table)").strip()
        if html and "<table" in html.lower() and "<table" not in md.lower():
            md = f"{md}\n\n{html}"
        return md, html or ""

    # Picture / chart
    if "picture" in type(element).__name__.lower() or label in {"picture", "chart"}:
        caption = ""
        try:
            caption = element.caption_text(doc=doc)  # type: ignore[call-arg]
        except Exception:  # noqa: BLE001
            caption = text
        caption = (caption or "figure").strip()
        return f"![{caption}](figure)", ""

    return text or f"({label or 'text'})", ""


def parse_docling_document(doc: Any, *, start_index: int = 1) -> dict[int, list[DetectionBlock]]:
    """DoclingDocument → page_number별 DetectionBlock 목록."""
    by_page: dict[int, list[DetectionBlock]] = {}
    index = start_index

    for element, _level in doc.iterate_items():
        block_type = map_docling_label(getattr(element, "label", None))
        if block_type is None:
            continue
        prov_list = getattr(element, "prov", None) or []
        if not prov_list:
            continue
        prov = prov_list[0]
        page_no = int(getattr(prov, "page_no", 1) or 1)
        page_w, page_h = _page_size(doc, page_no)
        bbox = _bbox_to_normalized(getattr(prov, "bbox", None), page_w=page_w, page_h=page_h)
        if bbox is None or bbox.w <= 0.001 or bbox.h <= 0.001:
            continue
        markdown, html = _element_markdown(element, doc)
        if not markdown.strip() and block_type not in {"figure", "table"}:
            continue
        block = DetectionBlock(
            id=str(index),
            index=index,
            page=page_no,
            type=block_type,
            bbox=bbox,
            markdown=markdown or f"({block_type})",
            html=html,
        )
        by_page.setdefault(page_no, []).append(block)
        index += 1

    for page_no, blocks in by_page.items():
        blocks.sort(key=lambda b: (b.bbox.y, b.bbox.x))
    return by_page


class DoclingEngine:
    """Docling DocumentConverter 래퍼."""

    def __init__(self) -> None:
        self._converter = None
        self._init_error: str | None = None

    @property
    def init_error(self) -> str | None:
        return self._init_error

    def _ensure(self):
        if self._converter is not None:
            return self._converter
        try:
            from docling.document_converter import DocumentConverter

            self._converter = DocumentConverter()
            logger.info("Docling DocumentConverter ready")
        except Exception as exc:  # noqa: BLE001
            self._init_error = str(exc)
            logger.exception("Failed to init Docling")
            self._converter = None
        return self._converter

    def convert_file(self, source_path: Path, *, start_index: int = 1) -> dict[int, list[DetectionBlock]]:
        """파일 경로를 DetectionBlock 페이지 맵으로 변환한다."""
        converter = self._ensure()
        if converter is None:
            return {}
        logger.info("Docling convert start path=%s", source_path.name)
        result = converter.convert(str(source_path))
        by_page = parse_docling_document(result.document, start_index=start_index)
        total = sum(len(v) for v in by_page.values())
        logger.info("Docling convert done pages=%s blocks=%s", len(by_page), total)
        return by_page


__all__ = ["DoclingEngine", "map_docling_label", "parse_docling_document"]
