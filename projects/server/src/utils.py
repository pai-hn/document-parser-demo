"""프로젝트 전역에서 사용하는 공통 유틸리티 함수.

반복적으로 사용되는 시간·UUID 생성 로직을 한 곳에서 관리합니다.

Usage::

    from src.utils import utc_now, new_uuid

    now = utc_now()          # timezone-aware UTC datetime
    uid = new_uuid()         # 시간순 정렬 가능한 UUID v7 (fallback: v4)
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

try:
    from uuid import uuid7  # type: ignore[attr-defined]
except ImportError:
    uuid7 = None


def utc_now() -> datetime:
    """현재 UTC 시각을 timezone-aware datetime으로 반환한다."""
    return datetime.now(UTC)


def new_uuid() -> UUID:
    """시간순 정렬이 가능한 UUID v7을 생성한다.

    Python 3.13 미만에서는 uuid7이 없으므로 uuid4로 대체한다.

    Returns:
        새로 생성된 UUID.
    """
    if uuid7 is not None:
        return uuid7()
    return uuid4()
