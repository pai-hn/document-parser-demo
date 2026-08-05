# 에러 처리

백엔드 예외 체계와 프론트엔드 에러 처리 방법입니다.

---

## 백엔드 예외 계층

`projects/server/src/common/exceptions.py`에 정의되어 있습니다.

```
AppException (500)
├─ BadRequestException (400)    — 잘못된 요청
├─ UnauthorizedException (401)  — 인증 실패
├─ ForbiddenException (403)     — 권한 부족
├─ NotFoundException (404)      — 리소스 없음
├─ ConflictException (409)      — 중복/충돌
└─ InvalidStateException (422)  — 상태 전이 불가
```

---

## 백엔드에서 예외 발생시키기

### 서비스에서

```python
from src.common.exceptions import NotFoundException, ForbiddenException

class NoticeService:
    async def get(self, notice_id: UUID) -> Notice:
        # BaseRepository.get_by_id()는 없으면 자동으로 NotFoundException 발생
        return await self._repo.get_by_id(notice_id)

    async def update(self, notice_id: UUID, current_user_id: UUID, ...) -> Notice:
        notice = await self._repo.get_by_id(notice_id)
        if notice.created_by != current_user_id:
            raise ForbiddenException("본인이 작성한 공지사항만 수정할 수 있습니다.")
        ...
```

### 도메인 모델에서

```python
@dataclass
class Notice:
    def update_content(self, *, title: str, updated_at: datetime) -> None:
        if not title.strip():
            raise ValueError("제목은 비어있을 수 없습니다.")
        self.title = title
        self.updated_at = updated_at
```

`ValueError`는 앱의 전역 예외 핸들러에서 422로 변환됩니다.

---

## API 에러 응답 형식

모든 에러는 동일한 JSON 구조로 반환됩니다.

```json
{
  "errorCode": "NOT_FOUND",
  "message": "Notice not found: 550e8400-...",
  "detail": null
}
```

---

## 프론트엔드에서 에러 처리

### getErrorMessage 유틸리티

`projects/frontend/src/api/client.ts`에 이미 정의된 함수를 사용합니다.

```tsx
import { getErrorMessage } from "@/api/client";

const handleCreate = async () => {
  try {
    await api.post("/notices", { title, content });
    toast.success("등록되었습니다.");
  } catch (err) {
    // 서버 응답의 message 또는 detail을 자동 추출
    toast.error(getErrorMessage(err, "등록에 실패했습니다."));
  }
};
```

### 네트워크 에러 vs 서버 에러 구분

```tsx
import Axios from "axios";

try {
  await api.post("/notices", data);
} catch (err) {
  if (Axios.isAxiosError(err)) {
    if (!err.response) {
      // 네트워크 에러 (서버 연결 불가)
      toast.error("서버에 연결할 수 없습니다.");
    } else if (err.response.status === 403) {
      toast.error("권한이 없습니다.");
    } else {
      toast.error(getErrorMessage(err, "요청에 실패했습니다."));
    }
  }
}
```

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `server/src/common/exceptions.py` | 예외 클래스 정의 |
| `server/webapp/app.py` | 전역 예외 핸들러 |
| `frontend/src/api/client.ts` | `getErrorMessage()`, 401 자동 리다이렉트 |
