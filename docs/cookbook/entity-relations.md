# 관계가 있는 엔티티

외래 키(FK)로 연결된 엔티티를 다루는 방법입니다.
예시로 Notice(공지사항)의 작성자(User) 정보를 함께 조회하는 패턴을 설명합니다.

---

## 현재 프로젝트의 관계

```
User (1) ──▶ (N) Sample     (created_by FK)
User (1) ──▶ (N) User       (team_id FK, 팀 소속)
```

---

## 백엔드: FK 컬럼 정의

### 도메인 모델

FK는 UUID 필드로 정의합니다. 도메인 모델에 다른 도메인 객체를 직접 포함하지 않습니다.

```python
@dataclass
class Notice:
    notice_id: UUID
    title: str
    content: str
    created_by: UUID   # ← User.user_id를 참조
    created_at: datetime
    updated_at: datetime
```

### 엔티티

```python
class NoticeEntity(Base[UUID, Notice]):
    __tablename__ = "notices"

    notice_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    # ...
```

### DB 스키마

```sql
CREATE TABLE notices (
    notice_id   UUID PRIMARY KEY,
    title       VARCHAR(255) NOT NULL,
    created_by  UUID NOT NULL REFERENCES users(user_id),  -- FK 제약
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 프론트엔드: 관계 데이터 표시하기

### 방법 1: 별도 API로 사용자 정보 조회 (권장)

SamplePage에서 사용하는 패턴입니다. 사용자 목록을 한 번 조회해서 맵으로 변환합니다.

```tsx
const [userMap, setUserMap] = useState<Record<string, string>>({});

useEffect(() => {
  api.get("/admin/users").then(({ data }) => {
    const map: Record<string, string> = {};
    for (const u of data) map[u.userId] = u.displayName || u.username;
    setUserMap(map);
  }).catch(() => {});
}, []);

// DataTable 컬럼에서
{
  key: "author",
  label: "작성자",
  getValue: (n) => userMap[n.createdBy] ?? "",
  render: (n) => <span className="text-muted-foreground">{userMap[n.createdBy] ?? "-"}</span>,
}
```

### 방법 2: 응답 DTO에 관계 데이터 포함

자주 함께 조회하는 경우, 서버에서 JOIN해서 반환합니다.

```python
# DTO
class NoticeWithAuthorResponse(CommonModel):
    notice_id: UUID
    title: str
    content: str
    created_by: UUID
    author_name: str | None   # ← JOIN 결과
    created_at: datetime

# 라우터
@router.get("/notices")
async def list_notices(notice_svc, user_svc):
    notices = await notice_svc.find_all()
    users = {u.user_id: u for u in await user_svc.find_all()}
    return [
        NoticeWithAuthorResponse(
            **asdict(n),
            author_name=users.get(n.created_by, None)
                and (users[n.created_by].display_name or users[n.created_by].username),
        )
        for n in notices
    ]
```

---

## MasterUsersPage의 "소속" 컬럼 패턴

User의 `team_id`가 다른 User(admin)의 `user_id`를 가리키는 자기참조 관계입니다.

```tsx
// 같은 데이터에서 관계를 해석
const userById = new Map(users.map((u) => [u.userId, u]));

{
  key: "teamId",
  label: "소속",
  getValue: (u) => {
    const admin = u.teamId ? userById.get(u.teamId) : null;
    return admin ? (admin.displayName || admin.username) : "";
  },
  render: (u) => {
    const admin = u.teamId ? userById.get(u.teamId) : null;
    return <span className="text-muted-foreground">{admin ? (admin.displayName || admin.username) : "-"}</span>;
  },
}
```
