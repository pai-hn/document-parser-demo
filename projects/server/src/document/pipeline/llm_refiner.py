"""선택적 LLM 마크다운 후처리 (OpenAI-compatible API)."""

from __future__ import annotations

import json
import logging

import httpx

from src.document.domains import DetectionBlock
from src.document.settings import DocumentSettings

logger = logging.getLogger(__name__)


class LlmMarkdownRefiner:
    """DetectionBlock.markdown을 LLM으로 가볍게 정리한다."""

    def __init__(self, settings: DocumentSettings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return bool(
            self._settings.document_llm_enabled
            and self._settings.document_llm_api_key
            and self._settings.document_llm_model
        )

    async def refine_blocks(
        self,
        blocks: list[DetectionBlock],
        *,
        force: bool = False,
    ) -> list[DetectionBlock]:
        """활성화된 경우 텍스트/표 블록 마크다운을 한 번에 정리한다.

        force=True 이면 DOCUMENT_LLM_ENABLED 와 무관하게 API 키만 있으면 실행한다
        (UI에서 Layout+OCR+LLM 선택 시).
        """
        can_run = force or self.enabled
        if not can_run or not blocks:
            return blocks
        if not (self._settings.document_llm_api_key and self._settings.document_llm_model):
            return blocks

        targets = [
            b
            for b in blocks
            if b.type in {"text", "marginalia", "table"} and b.markdown.strip()
        ]
        if not targets:
            return blocks

        # 페이지당 최대 12개만, 단일 요청으로 처리 (순차 40회 호출로 타임아웃 나던 문제 방지)
        batch = targets[:12]
        try:
            polished_map = await self._polish_batch(batch)
            for block in batch:
                polished = polished_map.get(block.id)
                if polished:
                    block.update_markdown(markdown=polished)
        except Exception:  # noqa: BLE001
            logger.warning("LLM batch refine failed; keeping OCR text", exc_info=True)
        return blocks

    async def _polish_batch(self, blocks: list[DetectionBlock]) -> dict[str, str]:
        base = self._settings.document_llm_base_url.rstrip("/")
        url = f"{base}/chat/completions"
        payload_blocks = [
            {"id": b.id, "type": b.type, "markdown": b.markdown[:4000]} for b in blocks
        ]
        system = (
            "You clean OCR markdown for a document parser. "
            "Return a JSON object mapping block id to cleaned markdown string only. "
            "Keep meaning, fix obvious OCR errors, preserve tables as GFM. No commentary."
        )
        user = json.dumps(payload_blocks, ensure_ascii=False)
        headers = {
            "Authorization": f"Bearer {self._settings.document_llm_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._settings.document_llm_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(url, headers=headers, json=body)
            res.raise_for_status()
            data = res.json()
        content = str(data["choices"][0]["message"]["content"]).strip()
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            # sometimes model wraps as {"blocks": {...}}
            return {}
        if "blocks" in parsed and isinstance(parsed["blocks"], dict):
            parsed = parsed["blocks"]
        return {str(k): str(v) for k, v in parsed.items() if isinstance(v, str)}
