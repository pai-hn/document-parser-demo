# 다이얼로그 패턴

모달 다이얼로그를 만들고 사용하는 방법입니다.
비밀번호 초기화 다이얼로그(`ResetPasswordDialog`)를 참고하여 설명합니다.

---

## 기본 구조

`Dialog`는 열림/닫힘 상태를 부모가 관리합니다.

```tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

function MyDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>제목</DialogTitle>
          <DialogDescription>설명 텍스트</DialogDescription>
        </DialogHeader>
        <p>다이얼로그 내용</p>
      </DialogContent>
    </Dialog>
  );
}
```

부모에서 사용:

```tsx
const [showDialog, setShowDialog] = useState(false);

<Button onClick={() => setShowDialog(true)}>열기</Button>
<MyDialog open={showDialog} onOpenChange={setShowDialog} />
```

---

## 입력 폼이 있는 다이얼로그

비밀번호 초기화처럼, 입력을 받고 API를 호출하는 패턴입니다.

```tsx
// projects/frontend/src/components/ConfirmInputDialog.tsx

import { useState } from "react";
import { toast } from "sonner";
import api from "@/api/client";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  label: string;
  apiUrl: string;
  apiField: string;
  successMessage?: string;
}

export function ConfirmInputDialog({ open, onOpenChange, title, label, apiUrl, apiField, successMessage }: Props) {
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!value.trim()) { setError("값을 입력하세요."); return; }
    setError("");
    setSaving(true);
    try {
      await api.put(apiUrl, { [apiField]: value });
      toast.success(successMessage ?? "완료되었습니다.");
      setValue("");
      onOpenChange(false);
    } catch {
      setError("요청에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 pt-2">
          <div className="space-y-1.5">
            <Label>{label}</Label>
            <Input
              value={value}
              onChange={(e) => setValue(e.target.value)}
              type="password"
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>취소</Button>
            <Button onClick={handleSubmit} isPending={saving}>확인</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

---

## 삭제 확인 다이얼로그

위험한 작업 전에 사용자 확인을 받는 패턴입니다.

```tsx
function DeleteConfirmDialog({ open, onOpenChange, onConfirm, itemName }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  itemName: string;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>삭제 확인</DialogTitle>
          <DialogDescription>"{itemName}"을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.</DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>취소</Button>
          <Button variant="destructive" onClick={() => { onConfirm(); onOpenChange(false); }}>삭제</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

---

## 실제 사용 예시

`ResetPasswordDialog.tsx`를 참고하세요. TeamPage, MasterUsersPage에서 사용됩니다.
