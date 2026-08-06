"""Vision LLM 전담 Detection 엔진.

페이지 이미지를 OpenAI-compatible Vision API에 보내고
category + bbox[x1,y1,x2,y2] + markdown/html 블록 JSON을 받는다.
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import re
from pathlib import Path
from typing import cast

import httpx

from src.document.domains import BBox, BlockType, DetectionBlock
from src.document.settings import DocumentSettings

logger = logging.getLogger(__name__)

_VALID_TYPES: set[str] = {"text", "figure", "table", "marginalia", "logo"}

# paragraph/heading/header/caption → text, footer → marginalia
_CATEGORY_ALIASES: dict[str, BlockType] = {
    "text": "text",
    "heading": "text",
    "title": "text",
    "section_title": "text",
    "document_title": "text",
    "paragraph": "text",
    "list": "text",
    "content": "text",
    "caption": "text",
    "figure_caption": "text",
    "table_caption": "text",
    "header": "text",
    "page_header": "text",
    "footer": "marginalia",
    "page_footer": "marginalia",
    "page_number": "marginalia",
    "footnote": "marginalia",
    "marginalia": "marginalia",
    "figure": "figure",
    "image": "figure",
    "chart": "figure",
    "logo": "logo",
    "seal": "logo",
    "brand": "logo",
    "table": "table",
}

_SYSTEM_PROMPT = """You are a strict document layout parser.
Return ONLY a single JSON object. No markdown fences. No commentary. No trailing text.

Schema:
{
  "blocks": [
    {
      "category": "text" | "figure" | "table" | "marginalia" | "logo",
      "bbox": [x1, y1, x2, y2],
      "markdown": "string",
      "html": "string"
    }
  ]
}

Category rules (keep it simple):
- text: body copy, titles, headings, captions, page running titles in the content area
- figure: photos, diagrams, charts (not brand logos)
- logo: organization / brand marks (e.g. city emblem + name)
- table: tabular grids only
- marginalia: page number, footer lines, tiny edge notes (footer == marginalia)

Hard rules:
1) bbox MUST be normalized 0..1 as [x1, y1, x2, y2], origin top-left. Tight around visible ink only. Never include large empty whitespace.
2) Do NOT invent empty blocks. Skip blank regions.
3) A title above a table is category=text; the table itself is category=table. Do not merge them.
4) Prefer coherent text blocks; do not shatter one list into many tiny boxes, and do not wrap huge empty regions.
5) Tables: GFM markdown in "markdown" AND full <table>...</table> in "html".
6) Figures/logos: markdown like ![caption](figure) or ![logo](logo); html may be "".
7) Non-table categories: html may be "".
8) Prefer Korean text when the page is Korean.
9) Reading order: top-to-bottom, then left-to-right.
10) Output JSON only.
"""


def normalize_engine_name(engine: str | None) -> str:
    """프론트/쿼리 엔진 이름을 내부 모드로 정규화한다."""
    raw = (engine or "paddle").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "layout_ocr": "paddle",
        "paddle": "paddle",
        "layout_ocr_llm": "paddle_llm",
        "paddle_llm": "paddle_llm",
        "vision_llm": "vision_llm",
        "vision": "vision_llm",
        "llm": "vision_llm",
        "pymupdf": "pymupdf",
        "native": "pymupdf",
        "pymupdf_ocr": "pymupdf_ocr",
        "pymupdfocr": "pymupdf_ocr",
        "native_ocr": "pymupdf_ocr",
        "docling": "docling",
    }
    return aliases.get(raw, "paddle")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _parse_bbox(raw: object) -> BBox | None:
    """[x1,y1,x2,y2] 또는 {x,y,w,h} / {x1,y1,x2,y2} 를 파싱한다."""
    if isinstance(raw, (list, tuple)) and len(raw) >= 4:
        try:
            x1, y1, x2, y2 = (_clamp01(float(raw[i])) for i in range(4))
        except (TypeError, ValueError):
            return None
        box = BBox.from_xyxy(x1, y1, x2, y2)
    elif isinstance(raw, dict):
        if all(k in raw for k in ("x1", "y1", "x2", "y2")):
            try:
                box = BBox.from_xyxy(
                    _clamp01(float(raw["x1"])),
                    _clamp01(float(raw["y1"])),
                    _clamp01(float(raw["x2"])),
                    _clamp01(float(raw["y2"])),
                )
            except (TypeError, ValueError):
                return None
        elif all(k in raw for k in ("x", "y", "w", "h")):
            try:
                x = _clamp01(float(raw["x"]))
                y = _clamp01(float(raw["y"]))
                w = _clamp01(float(raw["w"]))
                h = _clamp01(float(raw["h"]))
            except (TypeError, ValueError):
                return None
            if x + w > 1.0:
                w = 1.0 - x
            if y + h > 1.0:
                h = 1.0 - y
            box = BBox(x=round(x, 4), y=round(y, 4), w=round(w, 4), h=round(h, 4))
        else:
            return None
    else:
        return None

    if box.w <= 0.001 or box.h <= 0.001:
        return None
    # 거의 빈 페이지 전체를 덮는 박스 거부 (허상 bbox)
    if box.w * box.h > 0.85:
        return None
    return box


def _resolve_category(item: dict) -> BlockType | None:
    raw = str(item.get("category") or item.get("type") or "").lower().strip()
    raw = raw.replace(" ", "_").replace("-", "_")
    return _CATEGORY_ALIASES.get(raw)


def _compose_markdown(*, category: BlockType, markdown: str, html: str) -> str:
    md = markdown.strip()
    html_s = html.strip()
    if category == "table":
        if not md and html_s:
            md = html_s
        elif md and html_s and "<table" in html_s.lower() and "<table" not in md.lower():
            md = f"{md}\n\n{html_s}"
    if category == "figure" and not md:
        md = "![figure](figure)"
    if category == "logo" and not md:
        md = "![logo](logo)"
    return md


def parse_vision_blocks(
    payload: object,
    *,
    page_number: int,
    start_index: int,
) -> list[DetectionBlock]:
    """Vision LLM JSON 응답을 DetectionBlock 목록으로 변환한다."""
    data = payload
    if isinstance(payload, str):
        text = payload.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            text = fence.group(1).strip()
        # 앞뒤 잡음 제거
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        data = json.loads(text)

    if not isinstance(data, dict):
        return []
    items = data.get("blocks")
    if not isinstance(items, list):
        return []

    blocks: list[DetectionBlock] = []
    index = start_index
    for item in items:
        if not isinstance(item, dict):
            continue
        category = _resolve_category(item)
        if category is None or category not in _VALID_TYPES:
            continue
        bbox = _parse_bbox(item.get("bbox"))
        if bbox is None:
            continue

        html = str(item.get("html") or "").strip()
        markdown = _compose_markdown(
            category=category,
            markdown=str(item.get("markdown") or item.get("text") or ""),
            html=html,
        )
        # 빈 텍스트 블록 제거 (figure/logo/table은 placeholder 허용)
        if not markdown.strip() and category not in {"figure", "logo", "table"}:
            continue
        if category == "table" and not markdown.strip() and not html:
            continue

        blocks.append(
            DetectionBlock(
                id=str(index),
                index=index,
                page=page_number,
                type=cast(BlockType, category),
                bbox=bbox,
                markdown=markdown or f"({category})",
                html=html,
            )
        )
        index += 1

    blocks.sort(key=lambda b: (b.bbox.y, b.bbox.x))
    for i, block in enumerate(blocks, start=start_index):
        block.id = str(i)
        block.index = i
    return blocks


class VisionLlmEngine:
    """페이지 이미지 → Vision LLM → DetectionBlock."""

    def __init__(self, settings: DocumentSettings) -> None:
        self._settings = settings

    @property
    def configured(self) -> bool:
        return bool(self._settings.document_llm_api_key and self._model)

    @property
    def _model(self) -> str:
        return (
            self._settings.document_vision_model
            or self._settings.document_llm_model
            or "gpt-4o-mini"
        )

    async def detect_page(
        self,
        *,
        image_path: Path,
        page_number: int,
        start_index: int,
        width: int,
        height: int,
    ) -> list[DetectionBlock]:
        """한 페이지 이미지를 Vision LLM으로 Detection한다."""
        del width, height
        if not self.configured:
            raise RuntimeError("Vision LLM is not configured (API key / model missing)")

        mime, _ = mimetypes.guess_type(str(image_path))
        mime = mime or "image/png"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        data_url = f"data:{mime};base64,{encoded}"

        base = self._settings.document_llm_base_url.rstrip("/")
        url = f"{base}/chat/completions"
        body = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Parse page {page_number}. "
                                "Categories: text|figure|table|marginalia|logo only. "
                                "Tight bbox [x1,y1,x2,y2]. JSON only."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                    ],
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._settings.document_llm_api_key}",
            "Content-Type": "application/json",
        }
        logger.info(
            "Vision LLM detect page=%s model=%s path=%s",
            page_number,
            self._model,
            image_path.name,
        )
        async with httpx.AsyncClient(timeout=180.0) as client:
            res = await client.post(url, headers=headers, json=body)
            res.raise_for_status()
            data = res.json()
        content = str(data["choices"][0]["message"]["content"]).strip()
        blocks = parse_vision_blocks(content, page_number=page_number, start_index=start_index)
        logger.info("Vision LLM page=%s blocks=%s", page_number, len(blocks))
        return blocks


__all__ = ["VisionLlmEngine", "normalize_engine_name", "parse_vision_blocks"]
