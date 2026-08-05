# 폼 입력과 검증

폼 상태 관리, 검증, 제출 패턴입니다.
백엔드 DTO 검증과 프론트엔드 클라이언트 검증을 함께 다룹니다.

---

## 기본 폼 패턴

```tsx
const [title, setTitle] = useState("");
const [content, setContent] = useState("");
const [saving, setSaving] = useState(false);
const [error, setError] = useState("");

const handleSubmit = async () => {
  // 1. 클라이언트 검증
  if (!title.trim()) { setError("제목을 입력하세요."); return; }

  // 2. API 호출
  setError("");
  setSaving(true);
  try {
    await api.post("/notices", { title, content });
    toast.success("등록되었습니다.");
    setTitle("");
    setContent("");
  } catch (err) {
    setError(getErrorMessage(err, "등록에 실패했습니다."));
  } finally {
    setSaving(false);
  }
};
```

```tsx
{/* JSX */}
<div className="space-y-4">
  <div className="space-y-1.5">
    <Label>제목</Label>
    <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="제목" />
  </div>
  <div className="space-y-1.5">
    <Label>내용</Label>
    <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={4}
      className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[2px]"
    />
  </div>
  {error && <p className="text-sm text-destructive">{error}</p>}
  <Button onClick={handleSubmit} isPending={saving}>등록</Button>
</div>
```

---

## 접이식 생성 폼

목록 페이지 상단에서 토글로 열고 닫는 패턴입니다. TeamPage, MasterUsersPage에서 사용됩니다.

```tsx
const [showForm, setShowForm] = useState(false);

<Button onClick={() => setShowForm(!showForm)} size="sm" variant={showForm ? "secondary" : "default"}>
  {showForm ? <><ChevronUp className="h-4 w-4" /> 닫기</> : <><Plus className="h-4 w-4" /> 등록</>}
</Button>

{showForm && (
  <Card>
    <CardHeader><CardTitle className="text-base">항목 등록</CardTitle></CardHeader>
    <CardContent>
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label className="text-xs">제목</Label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} className="w-40" />
        </div>
        <Button onClick={handleCreate} isPending={saving} size="sm">등록</Button>
        {error && <p className="self-center text-sm text-destructive">{error}</p>}
      </div>
    </CardContent>
  </Card>
)}
```

---

## 백엔드 DTO 검증

Pydantic이 자동으로 타입과 필수 필드를 검증합니다.

```python
# projects/server/webapp/dto.py

class NoticeCreateRequest(CommonModel):
    title: str                   # 필수
    content: str = ""            # 선택 (기본값 "")
    max_views: int | None = None # 선택 (None 허용)
```

검증 실패 시 422 응답이 자동 반환됩니다.

```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

---

## 비밀번호 폼 (AccountPage 패턴)

현재/새/확인 비밀번호를 받고 서버에서 검증하는 패턴입니다.

```tsx
const handlePasswordChange = async (e: FormEvent) => {
  e.preventDefault();
  setPwError("");

  // 클라이언트 검증
  if (newPw.length < 4) { setPwError("비밀번호는 4자 이상이어야 합니다."); return; }
  if (newPw !== confirmPw) { setPwError("새 비밀번호가 일치하지 않습니다."); return; }

  // 서버 검증 (현재 비밀번호 확인)
  try {
    await api.put("/account/password", { currentPassword: currentPw, newPassword: newPw });
    toast.success("비밀번호가 변경되었습니다.");
  } catch {
    setPwError("현재 비밀번호를 확인하세요.");
  }
};
```

---

## 실제 사용 예시

| 페이지 | 폼 유형 |
|--------|---------|
| `SampleNewPage.tsx` | 기본 생성 폼 |
| `TeamPage.tsx` | 접이식 생성 폼 |
| `MasterUsersPage.tsx` | 접이식 + Select 포함 |
| `AccountPage.tsx` | 비밀번호 변경 폼 |
