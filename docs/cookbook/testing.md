# 테스트 작성하기

백엔드 테스트를 작성하고 실행하는 방법입니다.
testcontainers로 실제 PostgreSQL 컨테이너를 사용합니다.

---

## 테스트 실행

```bash
cd projects/server

# 전체 테스트
uv run pytest

# 상세 출력
uv run pytest -v

# 특정 파일
uv run pytest tests/test_notice.py -v

# 특정 테스트 함수
uv run pytest tests/test_notice.py::test_create_notice -v

# unit 마커만
uv run pytest -m unit -v
```

---

## 도메인 모델 테스트

도메인 모델의 상태 전이 로직을 테스트합니다. DB가 필요 없습니다.

`projects/server/tests/unit/test_notice.py`:

```python
"""Notice 도메인 모델 테스트."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.notice.domains import Notice


def _make_notice(**kwargs) -> Notice:
    """테스트용 Notice 팩토리."""
    now = datetime.now(timezone.utc)
    defaults = dict(
        notice_id=uuid4(),
        title="테스트 공지",
        content="내용",
        created_by=uuid4(),
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return Notice(**defaults)


def test_update_content():
    notice = _make_notice()
    new_time = datetime.now(timezone.utc)

    notice.update_content(title="수정됨", content="새 내용", updated_at=new_time)

    assert notice.title == "수정됨"
    assert notice.content == "새 내용"
    assert notice.updated_at == new_time
```

---

## 서비스 통합 테스트

실제 DB를 사용합니다. `conftest.py`의 `session_factory` 픽스처가 testcontainers PostgreSQL을 제공합니다.

`projects/server/tests/integration/test_notice_service.py`:

```python
"""Notice 서비스 통합 테스트."""

import pytest

from src.notice.repository import NoticeRepository
from src.notice.service import NoticeService


@pytest.fixture
def notice_svc(session_factory):
    repo = NoticeRepository(session_factory=session_factory)
    return NoticeService(notice_repo=repo)


@pytest.mark.asyncio
async def test_create_and_find(notice_svc, sample_user_id):
    # 생성
    notice = await notice_svc.create("테스트", "내용", sample_user_id)
    assert notice.title == "테스트"

    # 조회
    found = await notice_svc.get(notice.notice_id)
    assert found.notice_id == notice.notice_id

    # 목록
    all_notices = await notice_svc.find_all()
    assert len(all_notices) >= 1


@pytest.mark.asyncio
async def test_delete(notice_svc, sample_user_id):
    notice = await notice_svc.create("삭제할 공지", "", sample_user_id)
    await notice_svc.delete(notice.notice_id)

    all_notices = await notice_svc.find_all()
    assert all(n.notice_id != notice.notice_id for n in all_notices)
```

---

## API 엔드포인트 테스트

httpx의 `AsyncClient`로 FastAPI 앱을 직접 테스트합니다.

```python
"""Notice API 테스트."""

import pytest
from httpx import ASGITransport, AsyncClient

from webapp.app import create_app


@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_list_notices(client, auth_headers):
    response = await client.get("/notices", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `tests/conftest.py` | 공통 픽스처 (DB 컨테이너, 세션, 이벤트 루프) |
| `tests/unit/` | 도메인 모델 단위 테스트 |
| `tests/integration/` | DB 통합 테스트 |
| `pyproject.toml` | pytest 설정 (마커, asyncio_mode) |
