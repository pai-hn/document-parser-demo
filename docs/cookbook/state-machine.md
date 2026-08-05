# 상태 머신 패턴

도메인 모델에서 상태 전이를 안전하게 관리하는 방법입니다.
Sample 도메인의 `draft → published → archived` 흐름을 예시로 설명합니다.

---

## 상태 전이 다이어그램

```
  ┌───────┐
  │ draft │──publish──▶┌───────────┐
  └───┬───┘            │ published │──archive──▶┌──────────┐
      │                └───────────┘            │ archived │
      └──────────archive───────────────────────▶└──────────┘
```

- `draft`: 편집 가능, 발행 가능, 아카이브 가능
- `published`: 편집 불가, 아카이브 가능
- `archived`: 모든 변경 불가

---

## 1단계: 도메인 모델에 상태 전이 정의

상태 변경은 **반드시 도메인 메서드**를 통해서만 수행합니다.
서비스에서 `sample.status = "published"` 같은 직접 할당은 금지입니다.

```python
# projects/server/src/sample/domains.py

@dataclass
class Sample:
    sample_id: UUID
    title: str
    content: str
    status: str  # "draft" | "published" | "archived"
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    def is_editable(self) -> bool:
        """편집 가능한 상태인지 확인한다."""
        return self.status == "draft"

    def publish(self, *, updated_at: datetime) -> None:
        """draft → published 상태로 전이한다.

        Raises:
            ValueError: 현재 상태가 draft가 아닐 때.
        """
        if self.status != "draft":
            raise ValueError(f"draft 상태에서만 발행 가능 (현재: {self.status})")
        self.status = "published"
        self.updated_at = updated_at

    def archive(self, *, updated_at: datetime) -> None:
        """archived 상태로 전이한다."""
        if self.status == "archived":
            raise ValueError("이미 아카이브된 상태")
        self.status = "archived"
        self.updated_at = updated_at

    def update_content(self, *, title: str, content: str, updated_at: datetime) -> None:
        """제목과 내용을 수정한다. draft 상태에서만 가능하다.

        Raises:
            ValueError: 편집 불가능한 상태일 때.
        """
        if not self.is_editable():
            raise ValueError(f"편집 불가능한 상태 (현재: {self.status})")
        self.title = title
        self.content = content
        self.updated_at = updated_at
```

---

## 2단계: 서비스에서 상태 전이 호출

```python
# projects/server/src/sample/service.py

async def publish(self, sample_id: UUID) -> Sample:
    sample = await self._sample_repo.get_by_id(sample_id)
    sample.publish(updated_at=utc_now())   # 도메인 메서드 호출
    await self._sample_repo.update(sample)  # DB 반영
    return sample
```

---

## 3단계: 라우터에서 상태 전이 엔드포인트

```python
# projects/server/webapp/routers/sample.py

@router.post("/samples/{sample_id}/publish")
async def publish_sample(sample_id: UUID, ...):
    sample = await sample_svc.publish(sample_id)
    return SampleResponse.from_domain(sample)

@router.post("/samples/{sample_id}/archive")
async def archive_sample(sample_id: UUID, ...):
    sample = await sample_svc.archive(sample_id)
    return SampleResponse.from_domain(sample)
```

---

## 4단계: 프론트엔드에서 상태 전이 버튼

```tsx
const handlePublish = async (id: string) => {
  try {
    await api.post(`/samples/${id}/publish`);
    toast.success("발행되었습니다.");
    fetchSamples();
  } catch {
    toast.error("발행에 실패했습니다.");
  }
};

// DataTable 컬럼에서
{
  key: "actions",
  label: "작업",
  render: (s) => (
    <div className="flex gap-1">
      {s.status === "draft" && (
        <Button size="sm" variant="outline" onClick={() => handlePublish(s.sampleId)}>발행</Button>
      )}
      {s.status !== "archived" && (
        <Button size="sm" variant="ghost" onClick={() => handleArchive(s.sampleId)}>삭제</Button>
      )}
    </div>
  ),
}
```

---

## 5단계: 도메인 테스트

```python
def test_publish_from_draft():
    sample = _make_sample(status="draft")
    sample.publish(updated_at=datetime.now(timezone.utc))
    assert sample.status == "published"

def test_publish_from_published_raises():
    sample = _make_sample(status="published")
    with pytest.raises(ValueError, match="draft 상태에서만"):
        sample.publish(updated_at=datetime.now(timezone.utc))

def test_update_content_not_draft_raises():
    sample = _make_sample(status="published")
    with pytest.raises(ValueError, match="편집 불가능"):
        sample.update_content(title="x", content="y", updated_at=datetime.now(timezone.utc))
```

---

## 새 상태 머신을 설계할 때

1. **상태 목록과 전이 규칙**을 먼저 다이어그램으로 그리기
2. 각 전이를 **도메인 메서드**로 정의 (검증 포함)
3. 편집 가능 여부 같은 **파생 조건**도 메서드로 제공
4. 서비스는 도메인 메서드를 호출만 하고, 직접 상태를 바꾸지 않기
