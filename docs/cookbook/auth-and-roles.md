# 인증과 권한 관리

JWT 인증과 역할 기반 접근 제어(RBAC)를 사용하는 방법입니다.

---

## 역할 체계

| 역할 | 레벨 | 할 수 있는 것 |
|------|------|-------------|
| `member` | 1 | 일반 기능 사용, 본인 계정 관리 |
| `admin` | 2 | 팀 멤버 관리, member의 모든 권한 |
| `master` | 3 | 시스템 전체 관리, 모든 권한 |

---

## 백엔드: 엔드포인트에 권한 설정하기

### 로그인한 사용자만 접근

```python
# projects/server/webapp/routers/notice.py
from webapp.dependency import get_current_user

@router.post("/notices")
async def create_notice(
    current_user: Annotated[User, Depends(get_current_user)],
    ...
):
    # current_user.user_id, current_user.role 사용 가능
    notice = await notice_svc.create(body.title, current_user.user_id)
    ...
```

### 특정 역할 이상만 접근

```python
from webapp.dependency import require_min_role

@router.get("/admin/team/members")
async def list_team_members(
    current_user: Annotated[User, Depends(require_min_role("admin"))],
    ...
):
    # admin, master만 접근 가능
    ...
```

### 정확한 역할만 접근

```python
from webapp.dependency import require_role

@router.get("/admin/users")
async def list_users(
    current_user: Annotated[User, Depends(require_role("master"))],
    ...
):
    # master만 접근 가능
    ...
```

### 본인 리소스만 수정 가능

```python
from src.common.exceptions import ForbiddenException

@router.put("/notices/{notice_id}")
async def update_notice(
    notice_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    notice_svc: Annotated[NoticeService, Depends(notice_service_dependency)],
):
    notice = await notice_svc.get(notice_id)
    if notice.created_by != current_user.user_id:
        raise ForbiddenException("본인이 작성한 공지사항만 수정할 수 있습니다.")
    ...
```

---

## 프론트엔드: 역할별 UI 분기

### 라우트 보호

`projects/frontend/src/App.tsx`:

```tsx
{/* member 이상만 접근 */}
<Route element={<ProtectedRoute minRole="member"><MemberLayout /></ProtectedRoute>}>
  <Route path="home" element={<HomePage />} />
</Route>

{/* master만 접근 */}
<Route path="/master" element={<ProtectedRoute role="master"><MasterLayout /></ProtectedRoute>}>
  <Route index element={<MasterDashboardPage />} />
</Route>
```

### 컴포넌트에서 역할 확인

```tsx
import { useAuth } from "@/auth/AuthContext";

function SomeComponent() {
  const { auth } = useAuth();

  return (
    <div>
      {auth?.role === "admin" && <Button>팀 관리</Button>}
      {auth?.role === "master" && <Button>시스템 설정</Button>}
    </div>
  );
}
```

### 사이드바에서 역할별 메뉴

`projects/frontend/src/components/layout/Sidebar.tsx`:

```tsx
{/* admin 이상만 표시 */}
{auth?.role === "admin" && (
  <Link to="/team" className={navLinkClass("/team", true)}>
    <Users className="h-[18px] w-[18px] shrink-0" />
    {!collapsed && <span className="truncate">팀 관리</span>}
  </Link>
)}
```

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `server/src/auth/service.py` | JWT 토큰 생성/검증 |
| `server/src/auth/settings.py` | 토큰 만료 시간 설정 |
| `server/src/user/domains.py` | User 도메인 모델 (역할 체계) |
| `server/webapp/dependency.py` | `get_current_user`, `require_role`, `require_min_role` |
| `frontend/src/auth/AuthContext.tsx` | 인증 상태 관리 |
| `frontend/src/auth/ProtectedRoute.tsx` | 라우트 보호 |
