# 캐싱 (Redis)

Redis를 사용하여 자주 조회하는 데이터를 캐싱하는 방법입니다.

> 프로젝트 생성 시 `with_redis` 옵션이 활성화되어 있어야 합니다.

---

## 1단계: 인프라 확인

```bash
cd deploy/docker-compose && docker compose ps
# redis 컨테이너가 실행 중인지 확인
```

---

## 2단계: 서비스에서 캐시 사용하기

### 2-1. 서비스에 Redis 주입

`projects/server/src/sample/container.py`:

```python
from dependency_injector import containers, providers
from src.sample.repository import SampleRepository
from src.sample.service import SampleService


class SampleContainer(containers.DeclarativeContainer):
    database = providers.DependenciesContainer()
    redis = providers.DependenciesContainer()  # ← 추가

    sample_repo = providers.Singleton(SampleRepository, session_factory=database.session_factory)
    service = providers.Singleton(
        SampleService,
        sample_repo=sample_repo,
        redis_repo=redis.repository,  # ← 추가
    )
```

`projects/server/webapp/container.py`에서 연결:

```python
sample = providers.Container(SampleContainer, database=database, redis=redis)
```

### 2-2. 서비스에 캐시 로직 추가

```python
import json

from src.storages.redis.repository import RedisRepository


class SampleService:
    def __init__(self, sample_repo: SampleRepository, redis_repo: RedisRepository):
        self._sample_repo = sample_repo
        self._redis = redis_repo

    async def get_sample(self, sample_id: UUID) -> Sample:
        """캐시를 먼저 확인하고, 없으면 DB에서 조회한다."""
        cache_key = f"sample:{sample_id}"

        # 캐시 히트
        cached = await self._redis.client.get(cache_key)
        if cached:
            data = json.loads(cached)
            return Sample(**data)

        # 캐시 미스 → DB 조회 → 캐시 저장
        sample = await self._sample_repo.get_by_id(sample_id)
        await self._redis.client.set(
            cache_key,
            json.dumps(asdict(sample), default=str),
            ex=3600,  # 1시간 TTL
        )
        return sample
```

### 2-3. 데이터 변경 시 캐시 무효화

```python
    async def update_content(self, sample_id: UUID, title: str, content: str) -> Sample:
        sample = await self._sample_repo.get_by_id(sample_id)
        sample.update_content(title=title, content=content, updated_at=utc_now())
        await self._sample_repo.update(sample)

        # 캐시 무효화
        await self._redis.client.delete(f"sample:{sample_id}")

        return sample
```

---

## 환경 변수

```bash
REDIS_URL=redis://localhost:6379/0
```

## 관련 파일

| 파일 | 역할 |
|------|------|
| `server/src/storages/redis/settings.py` | Redis 연결 설정 |
| `server/src/storages/redis/repository.py` | Redis 클라이언트 래퍼 |
