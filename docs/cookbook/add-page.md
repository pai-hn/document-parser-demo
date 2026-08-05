# 새 페이지 추가하기

DB 테이블 → 백엔드 API → 프론트엔드 페이지 → 사이드바 메뉴까지,
**"공지사항"** 기능을 처음부터 끝까지 만드는 과정입니다.

이 가이드를 따라하면 공지사항을 생성·조회·삭제할 수 있는 완전한 페이지가 완성됩니다.

> 각 단계의 상세한 설명은 [새 도메인 추가하기](add-domain.md)를 참고하세요.

---

## 1단계: DB 테이블 생성

`deploy/docker-compose/init.sql`에 테이블을 추가합니다.

```sql
-- ── Notices ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notices (
    notice_id   UUID PRIMARY KEY,
    title       VARCHAR(255) NOT NULL,
    content     TEXT NOT NULL DEFAULT '',
    created_by  UUID NOT NULL REFERENCES users(user_id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

DB를 재생성합니다.

```bash
cd deploy/docker-compose && docker compose down -v && docker compose up -d
```

---

## 2단계: 백엔드 도메인 만들기

### 2-1. 디렉토리 생성

```bash
mkdir -p projects/server/src/notice
touch projects/server/src/notice/__init__.py
```

### 2-2. 도메인 모델

`projects/server/src/notice/domains.py`:

```python
"""Notice 도메인 모델."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Notice:
    """공지사항."""

    notice_id: UUID
    title: str
    content: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    def update_content(self, *, title: str, content: str, updated_at: datetime) -> None:
        """제목과 내용을 수정한다."""
        self.title = title
        self.content = content
        self.updated_at = updated_at
```

### 2-3. 엔티티

`projects/server/src/notice/entities.py`:

```python
"""Notice 엔티티."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import TIMESTAMP, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.notice.domains import Notice
from src.storages.database.base import Base


class NoticeEntity(Base[UUID, Notice]):
    __tablename__ = "notices"

    notice_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    @staticmethod
    def from_domain(domain: Notice) -> "NoticeEntity":
        return NoticeEntity(
            notice_id=domain.notice_id, title=domain.title, content=domain.content,
            created_by=domain.created_by, created_at=domain.created_at, updated_at=domain.updated_at,
        )

    def to_domain(self) -> Notice:
        return Notice(
            notice_id=self.notice_id, title=self.title, content=self.content,
            created_by=self.created_by, created_at=self.created_at, updated_at=self.updated_at,
        )

    def update(self, domain: Notice) -> None:
        self.title = domain.title
        self.content = domain.content
        self.updated_at = domain.updated_at

    def primary_key(self) -> UUID:
        return self.notice_id
```

### 2-4. 레포지토리

`projects/server/src/notice/repository.py`:

```python
"""Notice 레포지토리."""

from uuid import UUID

from src.notice.domains import Notice
from src.notice.entities import NoticeEntity
from src.storages.database.repository import BaseRepository


class NoticeRepository(BaseRepository[UUID, Notice]):
    entity: type[NoticeEntity] = NoticeEntity
```

### 2-5. 서비스

`projects/server/src/notice/service.py`:

```python
"""Notice 서비스."""

from uuid import UUID

from src.notice.domains import Notice
from src.notice.repository import NoticeRepository
from src.utils import new_uuid, utc_now


class NoticeService:
    """공지사항 CRUD를 담당한다."""

    def __init__(self, notice_repo: NoticeRepository):
        self._repo = notice_repo

    async def create(self, title: str, content: str, created_by: UUID) -> Notice:
        """새 공지사항을 생성한다."""
        now = utc_now()
        notice = Notice(
            notice_id=new_uuid(), title=title, content=content,
            created_by=created_by, created_at=now, updated_at=now,
        )
        await self._repo.create(notice)
        return notice

    async def find_all(self) -> list[Notice]:
        """전체 공지사항을 반환한다."""
        return await self._repo.find_all()

    async def get(self, notice_id: UUID) -> Notice:
        """공지사항을 ID로 조회한다."""
        return await self._repo.get_by_id(notice_id)

    async def delete(self, notice_id: UUID) -> None:
        """공지사항을 삭제한다."""
        await self._repo.delete(notice_id)
```

### 2-6. DI 컨테이너

`projects/server/src/notice/container.py`:

```python
"""Notice DI 컨테이너."""

from dependency_injector import containers, providers

from src.notice.repository import NoticeRepository
from src.notice.service import NoticeService


class NoticeContainer(containers.DeclarativeContainer):
    database = providers.DependenciesContainer()
    notice_repo = providers.Singleton(NoticeRepository, session_factory=database.session_factory)
    service = providers.Singleton(NoticeService, notice_repo=notice_repo)
```

---

## 3단계: API 엔드포인트 연결

### 3-1. 루트 컨테이너에 등록

`projects/server/webapp/container.py`:

```python
from src.notice.container import NoticeContainer

class ApplicationContainer(containers.DeclarativeContainer):
    # ... 기존 코드 ...
    notice = providers.Container(NoticeContainer, database=database)  # ← 추가
```

### 3-2. DTO 추가

`projects/server/webapp/dto.py`에 추가합니다.

```python
# --- Notice DTO ---

class NoticeCreateRequest(CommonModel):
    """공지사항 생성 요청."""
    title: str
    content: str = ""

class NoticeResponse(CommonModel):
    """공지사항 응답."""
    notice_id: UUID
    title: str
    content: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime
```

### 3-3. 의존성 함수

`projects/server/webapp/dependency.py`에 추가합니다.

```python
from src.notice.service import NoticeService

@inject
async def notice_service_dependency(
    service: NoticeService = Depends(Provide[ApplicationContainer.notice.service]),
) -> NoticeService:
    return service
```

### 3-4. 라우터 생성

`projects/server/webapp/routers/notice.py`:

```python
"""공지사항 엔드포인트."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.notice.service import NoticeService
from src.user.domains import User
from webapp.dependency import get_current_user, notice_service_dependency
from webapp.dto import NoticeCreateRequest, NoticeResponse

router = APIRouter()


@router.post("/notices", response_model=NoticeResponse, status_code=201)
async def create_notice(
    body: NoticeCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    notice_svc: Annotated[NoticeService, Depends(notice_service_dependency)],
):
    notice = await notice_svc.create(body.title, body.content, current_user.user_id)
    return NoticeResponse.from_domain(notice)


@router.get("/notices", response_model=list[NoticeResponse])
async def list_notices(
    notice_svc: Annotated[NoticeService, Depends(notice_service_dependency)],
):
    notices = await notice_svc.find_all()
    return [NoticeResponse.from_domain(n) for n in notices]


@router.delete("/notices/{notice_id}", status_code=204)
async def delete_notice(
    notice_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    notice_svc: Annotated[NoticeService, Depends(notice_service_dependency)],
):
    await notice_svc.delete(notice_id)
```

### 3-5. 앱에 라우터 마운트

`projects/server/webapp/app.py`의 `create_app()` 안에:

```python
from webapp.routers import notice
app.include_router(notice.router, tags=["Notice"])
```

### 3-6. 백엔드 확인

서버를 실행하고 Swagger에서 API가 동작하는지 확인합니다.

```bash
cd projects/server
uv run uvicorn webapp.app:create_app --factory --reload --host 0.0.0.0 --port 8080
# → http://localhost:8080/docs 에서 /notices 엔드포인트 확인
```

---

## 4단계: 프론트엔드 페이지 만들기

### 4-1. 페이지 컴포넌트

`projects/frontend/src/pages/NoticePage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable, type DataTableColumn } from "@/components/ui/data-table";
import { PageLayout } from "@/components/layout/PageLayout";
import { formatDate } from "@/lib/format";

interface Notice {
  noticeId: string;
  title: string;
  content: string;
  createdBy: string;
  createdAt: string;
}

export default function NoticePage() {
  const { auth } = useAuth();
  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchNotices = () => {
    setLoading(true);
    api.get("/notices").then(({ data }) => setNotices(data)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(fetchNotices, []);

  const handleCreate = async () => {
    if (!title.trim()) return;
    setSaving(true);
    try {
      await api.post("/notices", { title, content });
      toast.success("공지사항이 등록되었습니다.");
      setTitle("");
      setContent("");
      setShowForm(false);
      fetchNotices();
    } catch {
      toast.error("등록에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/notices/${id}`);
      toast.success("삭제되었습니다.");
      fetchNotices();
    } catch {
      toast.error("삭제에 실패했습니다.");
    }
  };

  const columns: DataTableColumn<Notice>[] = [
    { key: "title", label: "제목", sortable: true, searchable: true, render: (n) => <span className="font-medium">{n.title}</span> },
    { key: "createdAt", label: "등록일", sortable: true, dateFilter: true, getValue: (n) => n.createdAt, render: (n) => <span className="text-muted-foreground">{formatDate(n.createdAt)}</span> },
    {
      key: "actions", label: "작업", className: "text-right",
      render: (n) => (
        <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); handleDelete(n.noticeId); }}>
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      ),
    },
  ];

  return (
    <PageLayout
      title="공지사항"
      description="공지사항을 등록하고 관리합니다."
      actions={
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4" /> 등록
        </Button>
      }
    >
      {showForm && (
        <Card>
          <CardHeader><CardTitle className="text-base">공지사항 등록</CardTitle></CardHeader>
          <CardContent className="space-y-3 max-w-lg">
            <div className="space-y-1">
              <Label className="text-xs">제목</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="제목" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">내용</Label>
              <textarea
                value={content} onChange={(e) => setContent(e.target.value)}
                rows={4} placeholder="내용"
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[2px]"
              />
            </div>
            <Button onClick={handleCreate} isPending={saving} size="sm">등록</Button>
          </CardContent>
        </Card>
      )}

      <DataTable
        columns={columns}
        data={notices}
        loading={loading}
        emptyMessage="아직 공지사항이 없습니다."
        rowKey={(n) => n.noticeId}
      />
    </PageLayout>
  );
}
```

### 4-2. 라우트 등록

`projects/frontend/src/App.tsx`에서:

```tsx
// import 추가
import NoticePage from "@/pages/NoticePage";

// MemberLayout 라우트 블록 안에 추가
<Route path="notice" element={<NoticePage />} />
```

### 4-3. 사이드바 메뉴 추가

`projects/frontend/src/components/layout/Sidebar.tsx`:

```tsx
// import에 아이콘 추가
import { Home, FileText, ..., Megaphone } from "lucide-react";

// NAV_ITEMS에 추가
const NAV_ITEMS = [
  { to: "/home", label: "홈", icon: Home, exact: true },
  { to: "/sample", label: "Sample", icon: FileText },
  { to: "/notice", label: "공지사항", icon: Megaphone },  // ← 추가
];
```

---

## 5단계: 확인

```bash
# 1) 인프라 실행 중인지 확인
docker compose -f deploy/docker-compose/docker-compose.yml ps

# 2) 서버 실행
cd projects/server && uv run uvicorn webapp.app:create_app --factory --reload --host 0.0.0.0 --port 8080

# 3) 프론트 실행
cd projects/frontend && pnpm dev
```

http://localhost:5173/notice 에서 공지사항을 등록, 조회, 삭제할 수 있습니다.

---

## 체크리스트

- [ ] `deploy/docker-compose/init.sql` — 테이블 추가
- [ ] `src/notice/` — domains, entities, repository, service, container
- [ ] `webapp/container.py` — NoticeContainer 등록
- [ ] `webapp/dto.py` — NoticeCreateRequest, NoticeResponse
- [ ] `webapp/dependency.py` — notice_service_dependency
- [ ] `webapp/routers/notice.py` — API 엔드포인트
- [ ] `webapp/app.py` — 라우터 마운트
- [ ] `pages/NoticePage.tsx` — 페이지 컴포넌트
- [ ] `App.tsx` — 라우트 등록
- [ ] `Sidebar.tsx` — 메뉴 추가
