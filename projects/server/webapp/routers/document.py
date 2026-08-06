"""Document Detection 엔드포인트.

인증 없이 데모용으로 사용한다.
"""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from src.document.service import SAMPLES_DIR, DocumentService
from webapp.dependency import document_service_dependency
from webapp.dto import DetectionResultResponse, SampleProjectResponse

router = APIRouter(prefix="/documents")

_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}


def _file_response(path: Path) -> FileResponse:
    media_type = _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path, media_type=media_type)


@router.get("/samples", response_model=list[SampleProjectResponse])
async def list_samples(
    document_svc: Annotated[DocumentService, Depends(document_service_dependency)],
):
    """데모용 샘플 프로젝트 목록을 반환한다."""
    samples = document_svc.list_samples()
    return [SampleProjectResponse.from_domain(s) for s in samples]


@router.get("/samples/{sample_id}/thumbnail")
async def get_sample_thumbnail(
    sample_id: str,
    document_svc: Annotated[DocumentService, Depends(document_service_dependency)],
):
    """샘플 썸네일 이미지를 반환한다."""
    sample = document_svc.get_sample(sample_id)
    path = SAMPLES_DIR / sample.filename
    return _file_response(path)


@router.post("/samples/{sample_id}/detect", response_model=DetectionResultResponse)
async def detect_sample(
    sample_id: str,
    document_svc: Annotated[DocumentService, Depends(document_service_dependency)],
):
    """샘플 문서에 대해 Detection을 수행한다."""
    result = await document_svc.detect_sample(sample_id)
    return DetectionResultResponse.from_domain(result)


@router.post("/detect", response_model=DetectionResultResponse, status_code=201)
async def detect_upload(
    document_svc: Annotated[DocumentService, Depends(document_service_dependency)],
    file: UploadFile = File(...),
):
    """업로드된 PDF의 전체 페이지 Detection을 수행한다."""
    content = await file.read()
    filename = file.filename or "upload.bin"
    result = await document_svc.detect_upload(filename=filename, content=content)
    return DetectionResultResponse.from_domain(result)


@router.get("/{document_id}", response_model=DetectionResultResponse)
async def get_document(
    document_id: UUID,
    document_svc: Annotated[DocumentService, Depends(document_service_dependency)],
):
    """Detection 결과를 조회한다."""
    result = await document_svc.get_document(document_id)
    return DetectionResultResponse.from_domain(result)


@router.get("/{document_id}/pages/{page_number}/image")
async def get_document_page_image(
    document_id: UUID,
    page_number: int,
    document_svc: Annotated[DocumentService, Depends(document_service_dependency)],
):
    """문서의 특정 페이지 미리보기 이미지를 반환한다."""
    path: Path = await document_svc.get_page_image_path(document_id, page_number)
    return _file_response(path)


@router.get("/{document_id}/image")
async def get_document_image(
    document_id: UUID,
    document_svc: Annotated[DocumentService, Depends(document_service_dependency)],
):
    """문서 첫 페이지 미리보기 이미지를 반환한다 (하위 호환)."""
    path: Path = await document_svc.get_image_path(document_id)
    return _file_response(path)
