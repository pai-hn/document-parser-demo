"""Paddle layout 라벨 → 도메인 BlockType 매핑."""

from __future__ import annotations

from src.document.domains import BlockType

_LABEL_MAP: dict[str, BlockType] = {
    # text
    "text": "text",
    "title": "text",
    "paragraph_title": "text",
    "document_title": "text",
    "heading": "text",
    "header": "text",
    "paragraph": "text",
    "caption": "text",
    "abstract": "text",
    "content": "text",
    "reference": "text",
    "references": "text",
    "figure_caption": "text",
    "table_caption": "text",
    "figure_title": "text",
    "equation": "text",
    "formula": "text",
    "algorithm": "text",
    "list": "text",
    # figure / logo
    "figure": "figure",
    "image": "figure",
    "chart": "figure",
    "header_image": "logo",
    "footer_image": "logo",
    "logo": "logo",
    "seal": "logo",
    # table
    "table": "table",
    # footer == marginalia
    "footer": "marginalia",
    "page_number": "marginalia",
    "number": "marginalia",
    "footnote": "marginalia",
    "aside_text": "marginalia",
    "sidebar_text": "marginalia",
    "marginalia": "marginalia",
}


def map_label(label: str | None) -> BlockType | None:
    """레이아웃 라벨을 BlockType으로 변환한다. 무시할 라벨은 None."""
    if not label:
        return None
    key = label.strip().lower().replace(" ", "_").replace("-", "_")
    return _LABEL_MAP.get(key)
