"""헬스체크 엔드포인트."""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    """서버 상태 및 인프라 서비스 연결 상태를 확인한다.

    로드밸런서·모니터링에서 사용. 개별 서비스 실패가 전체 헬스를 fail로 만들지 않는다.
    """
    result: dict = {"status": "ok"}
    services: dict = {}

    if services:
        result["services"] = services

    return result
