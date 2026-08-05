# API 클라이언트 구조

프론트엔드의 API 호출 구조와 인증 토큰 자동 갱신 메커니즘입니다.

파일: `projects/frontend/src/api/client.ts`

---

## 기본 사용법

```tsx
import api from "@/api/client";

// GET
const { data } = await api.get("/samples");

// POST
await api.post("/samples", { title: "제목", content: "내용" });

// PUT
await api.put(`/samples/${sampleId}`, { title: "수정됨" });

// DELETE
await api.delete(`/samples/${sampleId}`);
```

---

## 인증 흐름

API 클라이언트가 자동으로 처리하는 것들:

1. **모든 요청에 Bearer 토큰 자동 첨부**
   - localStorage의 `access_token`을 읽어서 `Authorization: Bearer <token>` 헤더에 넣음

2. **401 응답 시 자동 토큰 갱신**
   - `refresh_token`으로 새 `access_token`을 발급받음
   - 원래 요청을 자동으로 재시도
   - 갱신 중 다른 요청이 들어오면 큐에 쌓았다가 갱신 완료 후 일괄 재시도

3. **갱신 실패 시 로그인 페이지로 리다이렉트**
   - refresh_token도 만료되었으면 localStorage를 비우고 `/login`으로 이동

개발자가 신경 쓸 것은 없습니다. `api.get()`만 호출하면 됩니다.

---

## 에러 메시지 추출

```tsx
import { getErrorMessage } from "@/api/client";

try {
  await api.post("/notices", data);
} catch (err) {
  // 서버 응답의 message 또는 detail을 자동 추출
  const msg = getErrorMessage(err, "등록에 실패했습니다.");
  setError(msg);
}
```

서버 응답 형식:
```json
{ "message": "이미 존재하는 아이디입니다." }
// 또는
{ "detail": "Not found" }
```

`getErrorMessage`는 `message` → `detail` → fallback 순서로 추출합니다.

---

## 파일 업로드

`multipart/form-data`로 전송합니다.

```tsx
const formData = new FormData();
formData.append("file", file);

await api.post(`/samples/${sampleId}/image`, formData, {
  headers: { "Content-Type": "multipart/form-data" },
});
```

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `api/client.ts` | Axios 인스턴스, 인터셉터, 토큰 갱신 |
| `auth/AuthContext.tsx` | 로그인/로그아웃, 인증 상태 관리 |
| `lib/constants.ts` | localStorage 키 상수 (`TOKEN_KEY`, `REFRESH_KEY`) |
