# 전문 검색 (Elasticsearch)

Elasticsearch를 사용하여 텍스트 검색 기능을 추가하는 방법입니다.
예시로 Sample의 제목과 내용을 검색해봅니다.

> 프로젝트 생성 시 `with_elasticsearch` 옵션이 활성화되어 있어야 합니다.

---

## 1단계: 인프라 확인

```bash
cd deploy/docker-compose && docker compose ps
# elasticsearch 컨테이너가 실행 중인지 확인

# 연결 확인
curl http://localhost:9200
```

---

## 2단계: 백엔드 — 색인 및 검색 API

### 2-1. 의존성 함수 등록

`projects/server/webapp/dependency.py`:

```python
from src.storages.elasticsearch.repository import ElasticsearchRepository

@inject
async def es_repo_dependency(
    repo: ElasticsearchRepository = Depends(Provide[ApplicationContainer.elasticsearch.repository]),
) -> ElasticsearchRepository:
    return repo
```

### 2-2. 색인 유틸리티

Sample 생성/수정 시 Elasticsearch에 색인합니다.

```python
# projects/server/src/sample/service.py

async def _index_to_es(self, sample: Sample) -> None:
    """Sample을 Elasticsearch에 색인한다."""
    if not self._es_repo:
        return
    await self._es_repo.client.index(
        index="samples",
        id=str(sample.sample_id),
        document={
            "title": sample.title,
            "content": sample.content,
            "status": sample.status,
            "created_at": sample.created_at.isoformat(),
        },
    )
```

### 2-3. 검색 엔드포인트

`projects/server/webapp/routers/sample.py`에 추가:

```python
@router.get("/samples/search")
async def search_samples(
    q: str,
    es_repo: Annotated[ElasticsearchRepository, Depends(es_repo_dependency)],
):
    """Sample을 전문 검색한다."""
    result = await es_repo.client.search(
        index="samples",
        query={
            "multi_match": {
                "query": q,
                "fields": ["title^2", "content"],  # 제목에 가중치 2배
            }
        },
        size=50,
    )
    return [hit["_source"] for hit in result["hits"]["hits"]]
```

---

## 3단계: 프론트엔드 — 검색 UI

```tsx
const [query, setQuery] = useState("");
const [results, setResults] = useState([]);

const handleSearch = async () => {
  if (!query.trim()) return;
  const { data } = await api.get(`/samples/search?q=${encodeURIComponent(query)}`);
  setResults(data);
};
```

---

## 환경 변수

```bash
ES_URLS=http://localhost:9200
# 인증이 필요한 경우:
ES_USERNAME=elastic
ES_PASSWORD=changeme
```

## 관련 파일

| 파일 | 역할 |
|------|------|
| `server/src/storages/elasticsearch/settings.py` | ES 연결 설정 |
| `server/src/storages/elasticsearch/repository.py` | ES 클라이언트 래퍼 |
