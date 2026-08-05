# UI 컴포넌트 카탈로그

프로젝트에서 사용할 수 있는 공용 UI 컴포넌트 목록과 사용 예시입니다.
모든 컴포넌트는 `@/components/ui/`에 있습니다.

---

## Button

```tsx
import { Button } from "@/components/ui/button";

<Button>기본</Button>
<Button variant="secondary">보조</Button>
<Button variant="outline">외곽선</Button>
<Button variant="ghost">고스트</Button>
<Button variant="destructive">위험</Button>
<Button size="sm">작은</Button>
<Button size="icon"><Trash2 className="h-4 w-4" /></Button>
<Button isPending={saving}>저장 중...</Button>
```

---

## Input / Label

```tsx
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

<div className="space-y-1.5">
  <Label htmlFor="title">제목</Label>
  <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="제목 입력" />
</div>

{/* 비밀번호 */}
<Input type="password" />

{/* 검색 아이콘 포함 */}
<div className="relative">
  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
  <Input placeholder="검색..." className="pl-8" />
</div>
```

---

## Select

커스텀 드롭다운입니다. 옵션 배열과 onChange 콜백을 받습니다.

```tsx
import { Select } from "@/components/ui/select";

<Select
  value={role}
  onChange={setRole}
  options={[
    { value: "member", label: "멤버" },
    { value: "admin", label: "관리자" },
  ]}
  placeholder="역할 선택"
  className="w-40"
/>
```

---

## Badge

상태, 태그, 역할 등을 표시합니다.

```tsx
import { Badge } from "@/components/ui/badge";

<Badge>기본</Badge>
<Badge variant="secondary">보조</Badge>
<Badge variant="outline">외곽선</Badge>
<Badge variant="destructive">위험</Badge>

{/* 활성/비활성 상태 */}
<Badge variant={isActive ? "default" : "outline"}>
  {isActive ? "활성" : "비활성"}
</Badge>
```

---

## Card

정보를 묶어서 표시하는 컨테이너입니다.

```tsx
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

<Card>
  <CardHeader>
    <CardTitle>제목</CardTitle>
    <CardDescription>설명 텍스트</CardDescription>
  </CardHeader>
  <CardContent>
    <p>카드 내용</p>
  </CardContent>
</Card>

{/* 테이블을 감쌀 때는 패딩 제거 */}
<Card>
  <CardContent className="p-0">
    <Table>...</Table>
  </CardContent>
</Card>
```

---

## StatCard

대시보드 통계 카드입니다. 아이콘, 라벨, 값을 받습니다.

```tsx
import { StatCard } from "@/components/ui/stat-card";
import { Users, FileText } from "lucide-react";

<div className="grid gap-4 sm:grid-cols-3">
  <StatCard label="사용자" value={userCount} icon={Users} />
  <StatCard label="게시물" value={postCount} icon={FileText} />
  <StatCard label="대기 중" value={null} icon={Clock} />  {/* null이면 "--" 표시 */}
</div>
```

---

## DatePicker

캘린더 팝오버 기반 날짜 선택입니다. 값은 `"YYYY-MM-DD"` 문자열입니다.

```tsx
import { DatePicker } from "@/components/ui/date-picker";

<DatePicker
  value={date}
  onChange={setDate}
  placeholder="날짜 선택"
/>

{/* 날짜 범위 */}
<div className="flex items-center gap-2">
  <DatePicker value={from} onChange={setFrom} placeholder="시작일" />
  <span className="text-muted-foreground">~</span>
  <DatePicker value={to} onChange={setTo} placeholder="종료일" />
</div>
```

---

## Dialog

모달 다이얼로그입니다. 확인, 입력 폼 등에 사용합니다.
자세한 사용법은 [다이얼로그 패턴](dialogs.md)을 참고하세요.

---

## PageLayout

모든 페이지의 최상위 레이아웃입니다. 제목, 설명, 우측 상단 버튼을 받습니다.

```tsx
import { PageLayout } from "@/components/layout/PageLayout";

<PageLayout
  title="공지사항"
  description="공지사항을 관리합니다."
  actions={<Button size="sm"><Plus className="h-4 w-4" /> 등록</Button>}
>
  {/* 페이지 내용 */}
</PageLayout>
```

---

## DataTable

표준 테이블 컴포넌트입니다. 정렬, 검색, 날짜 필터를 기본 제공합니다.
자세한 사용법은 [DataTable 사용하기](data-table.md)를 참고하세요.
