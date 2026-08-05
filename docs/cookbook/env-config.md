# 환경 변수 관리

서버 설정을 환경 변수로 관리하는 방법입니다.

---

## .env 파일 설정

```bash
cd projects/server
cp .env.example .env
# .env 파일을 열어서 값을 수정합니다.
```

---

## 변수 목록

### 데이터베이스 (필수)

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myproject
DB_USER=postgres
DB_PASSWORD=postgres
```

설정 파일: `server/src/storages/database/settings.py`

### 인증

```bash
JWT_SECRET_KEY=your-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440    # 1일
REFRESH_TOKEN_EXPIRE_DAYS=7
```

설정 파일: `server/src/auth/settings.py`

### Redis (선택)

```bash
REDIS_URL=redis://localhost:6379/0
```

### MinIO (선택)

```bash
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=default
```

### Elasticsearch (선택)

```bash
ES_URLS=http://localhost:9200
```

---

## 새 설정 추가하기

### 1. Settings 클래스 만들기

`projects/server/src/notice/settings.py`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings


class NoticeSettings(BaseSettings):
    """공지사항 설정."""

    NOTICE_MAX_LENGTH: int = Field(default=10000, description="공지사항 최대 글자수")
    NOTICE_ALLOW_HTML: bool = Field(default=False, description="HTML 허용 여부")

    class Config:
        env_prefix = ""
```

### 2. 서비스에서 사용

```python
class NoticeService:
    def __init__(self, notice_repo: NoticeRepository, settings: NoticeSettings):
        self._repo = notice_repo
        self._settings = settings

    async def create(self, title: str, content: str, ...) -> Notice:
        if len(content) > self._settings.NOTICE_MAX_LENGTH:
            raise BadRequestException(f"내용은 {self._settings.NOTICE_MAX_LENGTH}자 이하여야 합니다.")
        ...
```

### 3. DI 컨테이너에서 주입

```python
class NoticeContainer(containers.DeclarativeContainer):
    database = providers.DependenciesContainer()
    settings = providers.Singleton(NoticeSettings)
    notice_repo = providers.Singleton(NoticeRepository, session_factory=database.session_factory)
    service = providers.Singleton(NoticeService, notice_repo=notice_repo, settings=settings)
```

### 4. .env에 값 설정

```bash
NOTICE_MAX_LENGTH=5000
NOTICE_ALLOW_HTML=true
```

> `pydantic-settings`는 환경 변수를 자동으로 읽어서 타입 변환합니다.
> `Field(default=...)` 값이 있으면 환경 변수를 설정하지 않아도 기본값이 사용됩니다.
