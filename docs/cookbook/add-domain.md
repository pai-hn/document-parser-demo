# 새 도메인 추가하기

백엔드에 DDD 구조로 새 도메인을 처음부터 끝까지 만드는 방법입니다.
예시로 **"Task"** 도메인(할 일 관리)을 추가해봅니다.

> 기존 `sample/` 디렉토리를 레퍼런스로 참고하면서 따라하면 됩니다.

---

## 0단계: 디렉토리 생성

```bash
mkdir -p projects/server/src/task
touch projects/server/src/task/__init__.py
```

---

## 1단계: 도메인 모델 — `domains.py`

상태 변경은 **반드시 메서드**를 통해서만 수행합니다. 서비스에서 직접 필드를 바꾸면 안 됩니다.

`projects/server/src/task/domains.py`:

```python
"""Task 도메인 모델.

할 일의 생명주기: todo → in_progress → done
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Task:
    """할 일 항목.

    Attributes:
        task_id: 고유 식별자.
        title: 제목.
        status: 현재 상태 ("todo", "in_progress", "done").
        assigned_to: 담당자 사용자 ID.
    """

    task_id: UUID
    title: str
    description: str
    status: str
    assigned_to: UUID
    created_at: datetime
    updated_at: datetime

    def start(self, *, updated_at: datetime) -> None:
        """todo → in_progress 상태로 전이한다.

        Raises:
            ValueError: 현재 상태가 todo가 아닐 때.
        """
        if self.status != "todo":
            raise ValueError(f"todo 상태에서만 시작 가능 (현재: {self.status})")
        self.status = "in_progress"
        self.updated_at = updated_at

    def complete(self, *, updated_at: datetime) -> None:
        """in_progress → done 상태로 전이한다.

        Raises:
            ValueError: 현재 상태가 in_progress가 아닐 때.
        """
        if self.status != "in_progress":
            raise ValueError(f"진행 중 상태에서만 완료 가능 (현재: {self.status})")
        self.status = "done"
        self.updated_at = updated_at
```

---

## 2단계: 엔티티 — `entities.py`

SQLAlchemy 테이블과 도메인 모델 사이의 매핑을 담당합니다.

`projects/server/src/task/entities.py`:

```python
"""Task 엔티티 — tasks 테이블 매핑."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import TIMESTAMP, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.storages.database.base import Base
from src.task.domains import Task


class TaskEntity(Base[UUID, Task]):
    __tablename__ = "tasks"

    task_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="todo")
    assigned_to: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    @staticmethod
    def from_domain(domain: Task) -> "TaskEntity":
        return TaskEntity(
            task_id=domain.task_id,
            title=domain.title,
            description=domain.description,
            status=domain.status,
            assigned_to=domain.assigned_to,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    def to_domain(self) -> Task:
        return Task(
            task_id=self.task_id,
            title=self.title,
            description=self.description,
            status=self.status,
            assigned_to=self.assigned_to,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def update(self, domain: Task) -> None:
        self.title = domain.title
        self.description = domain.description
        self.status = domain.status
        self.assigned_to = domain.assigned_to
        self.updated_at = domain.updated_at

    def primary_key(self) -> UUID:
        return self.task_id
```

---

## 3단계: 레포지토리 — `repository.py`

`BaseRepository`를 상속하면 `create`, `get_by_id`, `find_all`, `update`, `delete`는 자동 제공됩니다.
도메인에 특화된 쿼리만 추가하면 됩니다.

`projects/server/src/task/repository.py`:

```python
"""Task 레포지토리."""

from uuid import UUID

from sqlalchemy import select

from src.storages.database.repository import BaseRepository
from src.task.domains import Task
from src.task.entities import TaskEntity


class TaskRepository(BaseRepository[UUID, Task]):
    entity: type[TaskEntity] = TaskEntity

    async def find_by_assigned_to(self, user_id: UUID) -> list[Task]:
        """특정 사용자에게 배정된 Task를 모두 반환한다."""
        async with self.session_factory() as session:
            stmt = select(TaskEntity).where(TaskEntity.assigned_to == user_id)
            result = await session.execute(stmt)
            return [e.to_domain() for e in result.scalars().all()]
```

---

## 4단계: 서비스 — `service.py`

비즈니스 로직을 담당합니다. 도메인 메서드를 호출하고 레포지토리에 저장합니다.

`projects/server/src/task/service.py`:

```python
"""Task 서비스."""

from uuid import UUID

from src.task.domains import Task
from src.task.repository import TaskRepository
from src.utils import new_uuid, utc_now


class TaskService:
    """Task 도메인의 CRUD 및 상태 전이를 담당한다."""

    def __init__(self, task_repo: TaskRepository):
        self._task_repo = task_repo

    async def create_task(self, title: str, description: str, assigned_to: UUID) -> Task:
        """새 Task를 todo 상태로 생성한다."""
        now = utc_now()
        task = Task(
            task_id=new_uuid(),
            title=title,
            description=description,
            status="todo",
            assigned_to=assigned_to,
            created_at=now,
            updated_at=now,
        )
        await self._task_repo.create(task)
        return task

    async def get_task(self, task_id: UUID) -> Task:
        """Task를 ID로 조회한다."""
        return await self._task_repo.get_by_id(task_id)

    async def find_all(self) -> list[Task]:
        """전체 Task를 반환한다."""
        return await self._task_repo.find_all()

    async def start(self, task_id: UUID) -> Task:
        """Task를 시작한다 (todo → in_progress)."""
        task = await self._task_repo.get_by_id(task_id)
        task.start(updated_at=utc_now())
        await self._task_repo.update(task)
        return task

    async def complete(self, task_id: UUID) -> Task:
        """Task를 완료한다 (in_progress → done)."""
        task = await self._task_repo.get_by_id(task_id)
        task.complete(updated_at=utc_now())
        await self._task_repo.update(task)
        return task
```

---

## 5단계: DI 컨테이너 — `container.py`

`projects/server/src/task/container.py`:

```python
"""Task 도메인 DI 컨테이너."""

from dependency_injector import containers, providers

from src.task.repository import TaskRepository
from src.task.service import TaskService


class TaskContainer(containers.DeclarativeContainer):
    database = providers.DependenciesContainer()
    task_repo = providers.Singleton(TaskRepository, session_factory=database.session_factory)
    service = providers.Singleton(TaskService, task_repo=task_repo)
```

---

## 6단계: 루트 컨테이너에 등록

`projects/server/webapp/container.py`에 TaskContainer를 추가합니다.

```python
from src.task.container import TaskContainer

class ApplicationContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["webapp"])
    database = providers.Container(DatabaseContainer)
    user = providers.Container(UserContainer, database=database)
    auth = providers.Container(AuthContainer, user_repo=user.user_repo)
    sample = providers.Container(SampleContainer, database=database)
    task = providers.Container(TaskContainer, database=database)  # ← 추가
```

---

## 7단계: DTO 추가

`projects/server/webapp/dto.py`에 요청/응답 DTO를 추가합니다.

```python
# --- Task DTO ---

class TaskCreateRequest(CommonModel):
    """Task 생성 요청."""
    title: str
    description: str = ""

class TaskResponse(CommonModel):
    """Task 응답."""
    task_id: UUID
    title: str
    description: str
    status: str
    assigned_to: UUID
    created_at: datetime
    updated_at: datetime
```

> `TaskResponse`에 `from_domain`을 따로 만들 필요 없습니다.
> `CommonModel`이 이미 제공합니다.

---

## 8단계: 의존성 함수 등록

`projects/server/webapp/dependency.py`에 추가합니다.

```python
from src.task.service import TaskService

@inject
async def task_service_dependency(
    service: TaskService = Depends(Provide[ApplicationContainer.task.service]),
) -> TaskService:
    """TaskService를 DI 컨테이너에서 주입받는다."""
    return service
```

---

## 9단계: 라우터 추가

`projects/server/webapp/routers/task.py` 파일을 생성합니다.

```python
"""Task CRUD 엔드포인트."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.task.service import TaskService
from src.user.domains import User
from webapp.dependency import get_current_user, task_service_dependency
from webapp.dto import TaskCreateRequest, TaskResponse

router = APIRouter()


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    task_svc: Annotated[TaskService, Depends(task_service_dependency)],
):
    """새 Task를 생성한다."""
    task = await task_svc.create_task(
        title=body.title,
        description=body.description,
        assigned_to=current_user.user_id,
    )
    return TaskResponse.from_domain(task)


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    task_svc: Annotated[TaskService, Depends(task_service_dependency)],
):
    """전체 Task 목록을 반환한다."""
    tasks = await task_svc.find_all()
    return [TaskResponse.from_domain(t) for t in tasks]


@router.post("/tasks/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    task_svc: Annotated[TaskService, Depends(task_service_dependency)],
):
    """Task를 시작한다."""
    task = await task_svc.start(task_id)
    return TaskResponse.from_domain(task)


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    task_svc: Annotated[TaskService, Depends(task_service_dependency)],
):
    """Task를 완료한다."""
    task = await task_svc.complete(task_id)
    return TaskResponse.from_domain(task)
```

---

## 10단계: 라우터를 앱에 마운트

`projects/server/webapp/app.py`의 `create_app()` 함수에서 라우터를 등록합니다.

```python
from webapp.routers import task

app.include_router(task.router, tags=["Task"])
```

---

## 11단계: DB 테이블 생성

`deploy/docker-compose/init.sql`에 테이블을 추가합니다.

```sql
CREATE TABLE IF NOT EXISTS tasks (
    task_id       UUID PRIMARY KEY,
    title         VARCHAR(255) NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    status        VARCHAR(20) NOT NULL DEFAULT 'todo',
    assigned_to   UUID NOT NULL REFERENCES users(user_id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to);
```

이미 실행 중인 DB에 반영하려면:

```bash
# 방법 1: DB 재생성 (개발 환경)
cd deploy/docker-compose && docker compose down -v && docker compose up -d

# 방법 2: SQL 직접 실행 (데이터 유지)
docker compose exec postgres psql -U postgres -d <dbname> -c "
CREATE TABLE IF NOT EXISTS tasks (...);
"
```

---

## 12단계: 테스트

```bash
cd projects/server

# API 문서에서 확인
uv run uvicorn webapp.app:create_app --factory --reload --host 0.0.0.0 --port 8080
# → http://localhost:8080/docs 에서 /tasks 엔드포인트 확인

# 유닛 테스트 작성
uv run pytest tests/ -v
```

---

## 체크리스트

- [ ] `src/task/domains.py` — 도메인 모델
- [ ] `src/task/entities.py` — SQLAlchemy 엔티티
- [ ] `src/task/repository.py` — 레포지토리
- [ ] `src/task/service.py` — 서비스
- [ ] `src/task/container.py` — DI 컨테이너
- [ ] `webapp/container.py` — 루트 컨테이너에 등록
- [ ] `webapp/dto.py` — 요청/응답 DTO
- [ ] `webapp/dependency.py` — 의존성 함수
- [ ] `webapp/routers/task.py` — API 엔드포인트
- [ ] `webapp/app.py` — 라우터 마운트
- [ ] `deploy/docker-compose/init.sql` — DB 스키마
