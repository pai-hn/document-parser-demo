# DataTable 사용하기

`DataTable`은 이 프로젝트의 표준 테이블 컴포넌트입니다.
컬럼 정렬, 텍스트 검색, 필드 지정 검색, 날짜 범위 필터를 기본 제공합니다.

---

## 기본 사용법

```tsx
import { DataTable, type DataTableColumn } from "@/components/ui/data-table";

interface Task {
  taskId: string;
  title: string;
  assignee: string;
  createdAt: string;
}

const columns: DataTableColumn<Task>[] = [
  { key: "title", label: "제목", sortable: true, searchable: true },
  { key: "assignee", label: "담당자", sortable: true, searchable: true },
  { key: "createdAt", label: "생성일", sortable: true },
];

<DataTable
  columns={columns}
  data={tasks}
  loading={loading}
  emptyMessage="아직 할 일이 없습니다."
  rowKey={(t) => t.taskId}
/>
```

이것만으로 정렬과 검색이 작동하는 테이블이 완성됩니다.

---

## 컬럼 옵션

| 옵션 | 타입 | 설명 |
|------|------|------|
| `key` | `string` | 컬럼 고유 키 (필수) |
| `label` | `string` | 헤더에 표시할 텍스트 (필수) |
| `sortable` | `boolean` | 헤더 클릭으로 정렬 (asc → desc → 해제) |
| `searchable` | `boolean` | 텍스트 검색 대상에 포함 |
| `dateFilter` | `boolean` | 필드 선택 시 DatePicker로 전환 |
| `getValue` | `(row) => string` | 검색·정렬에 사용할 값. 미지정 시 `row[key]` |
| `render` | `(row) => ReactNode` | 셀 커스텀 렌더링 |
| `className` | `string` | `<th>`, `<td>`에 적용할 CSS 클래스 |

---

## 검색과 날짜 필터

`searchable` 컬럼과 `dateFilter` 컬럼이 **하나의 드롭다운**에 통합됩니다.

- **텍스트 필드 선택** (전체, 제목, 담당자 등) → 텍스트 검색 입력
- **날짜 필드 선택** (생성일, 수정일 등) → DatePicker 쌍(시작일 ~ 종료일)으로 전환

```tsx
const columns: DataTableColumn<Task>[] = [
  { key: "title", label: "제목", sortable: true, searchable: true },
  { key: "assignee", label: "담당자", sortable: true, searchable: true },
  {
    key: "createdAt",
    label: "생성일",
    sortable: true,
    dateFilter: true,                                 // ← 날짜 필터
    getValue: (t) => t.createdAt,                     // ISO 문자열 (필터·정렬용)
    render: (t) => formatDate(t.createdAt),            // 화면 표시용
  },
];
```

드롭다운: `[전체] [제목] [담당자] [생성일]`
- "전체" 선택 → `[🔍 검색...]`
- "생성일" 선택 → `[📅 시작일] ~ [📅 종료일]`

---

## 커스텀 셀 렌더링

```tsx
{
  key: "status",
  label: "상태",
  sortable: true,
  getValue: (t) => t.status,
  render: (t) => (
    <Badge variant={t.status === "done" ? "default" : "outline"}>
      {t.status === "done" ? "완료" : "진행 중"}
    </Badge>
  ),
}
```

---

## 액션 버튼 컬럼

`onRowClick`과 충돌하지 않도록 `e.stopPropagation()`을 호출합니다.

```tsx
{
  key: "actions",
  label: "작업",
  className: "text-right",
  render: (t) => (
    <Button
      variant="ghost" size="icon"
      onClick={(e) => { e.stopPropagation(); handleDelete(t.taskId); }}
    >
      <Trash2 className="h-3.5 w-3.5" />
    </Button>
  ),
}
```

---

## 행 클릭

```tsx
<DataTable
  columns={columns}
  data={tasks}
  rowKey={(t) => t.taskId}
  onRowClick={(task) => navigate(`/tasks/${task.taskId}`)}
/>
```

---

## 실제 사용 예시

`SamplePage.tsx`, `TeamPage.tsx`, `MasterUsersPage.tsx`를 참고하세요.
