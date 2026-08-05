# 파일 업로드 (MinIO)

MinIO(S3 호환 스토리지)를 사용하여 파일 업로드 기능을 추가하는 방법입니다.
예시로 Sample에 이미지를 첨부해봅니다.

> 프로젝트 생성 시 `with_minio` 옵션이 활성화되어 있어야 합니다.

---

## 1단계: 인프라 확인

```bash
cd deploy/docker-compose && docker compose ps
# minio 컨테이너가 실행 중인지 확인
# MinIO 콘솔: http://localhost:9001 (minioadmin / minioadmin)
```

---

## 2단계: 백엔드 — 업로드 엔드포인트 추가

### 2-1. 의존성 함수 등록

`projects/server/webapp/dependency.py`에 MinIO 의존성이 없다면 추가합니다.

```python
from src.storages.minio.repository import MinioRepository

@inject
async def minio_repo_dependency(
    repo: MinioRepository = Depends(Provide[ApplicationContainer.minio.repository]),
) -> MinioRepository:
    return repo
```

### 2-2. 업로드 엔드포인트

`projects/server/webapp/routers/sample.py`에 추가합니다.

```python
from fastapi import UploadFile

from webapp.dependency import minio_repo_dependency
from src.storages.minio.repository import MinioRepository


@router.post("/samples/{sample_id}/image")
async def upload_sample_image(
    sample_id: UUID,
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_user)],
    sample_svc: Annotated[SampleService, Depends(sample_service_dependency)],
    minio_repo: Annotated[MinioRepository, Depends(minio_repo_dependency)],
):
    """샘플에 이미지를 첨부한다."""
    # 파일을 MinIO에 업로드
    object_name = f"samples/{sample_id}/{file.filename}"
    minio_repo.client.put_object(
        minio_repo.bucket,
        object_name,
        file.file,
        file.size,
        content_type=file.content_type or "application/octet-stream",
    )

    return {"object_name": object_name, "size": file.size}
```

---

## 3단계: 프론트엔드 — 업로드 UI

페이지 컴포넌트에 파일 업로드 버튼을 추가합니다.

```tsx
const handleUpload = async (sampleId: string, file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  try {
    await api.post(`/samples/${sampleId}/image`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    toast.success("이미지가 업로드되었습니다.");
  } catch {
    toast.error("업로드에 실패했습니다.");
  }
};

// JSX
<input
  type="file"
  accept="image/*"
  onChange={(e) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(sample.sampleId, file);
  }}
/>
```

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `server/src/storages/minio/settings.py` | MinIO 연결 설정 |
| `server/src/storages/minio/repository.py` | MinIO 클라이언트 래퍼 |
| `deploy/docker-compose/docker-compose.yml` | MinIO 컨테이너 정의 |

## 환경 변수

```bash
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=default
```
