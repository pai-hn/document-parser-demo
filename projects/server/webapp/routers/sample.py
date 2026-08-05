"""Sample 도메인 CRUD 엔드포인트 — 새 라우터를 만들 때 참고하는 레퍼런스 구현.

이 파일은 표준 REST 엔드포인트 패턴을 보여줍니다:
- POST (생성), GET (목록/상세), PUT (수정), POST (상태 전이)
- 서비스 주입은 ``Annotated[SampleService, Depends(sample_service_dependency)]``
- 인증이 필요한 엔드포인트는 ``Depends(get_current_user)`` 추가
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.sample.service import SampleService
from src.user.domains import User
from webapp.dependency import get_current_user, sample_service_dependency
from webapp.dto import SampleCreateRequest, SampleResponse, SampleUpdateRequest

router = APIRouter()


@router.post("/samples", response_model=SampleResponse, status_code=201)
async def create_sample(
    body: SampleCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    sample_svc: Annotated[SampleService, Depends(sample_service_dependency)],
):
    """새 샘플을 draft 상태로 생성한다."""
    sample = await sample_svc.create_sample(
        title=body.title,
        content=body.content or "",
        created_by=current_user.user_id,
    )
    return SampleResponse.from_domain(sample)


@router.get("/samples", response_model=list[SampleResponse])
async def list_samples(
    sample_svc: Annotated[SampleService, Depends(sample_service_dependency)],
):
    """전체 샘플 목록을 반환한다 (archived 제외)."""
    samples = await sample_svc.find_all()
    return [SampleResponse.from_domain(s) for s in samples if s.status != "archived"]


@router.get("/samples/{sample_id}", response_model=SampleResponse)
async def get_sample(
    sample_id: UUID,
    sample_svc: Annotated[SampleService, Depends(sample_service_dependency)],
):
    """샘플 상세 정보를 반환한다."""
    sample = await sample_svc.get_sample(sample_id)
    return SampleResponse.from_domain(sample)


@router.put("/samples/{sample_id}", response_model=SampleResponse)
async def update_sample(
    sample_id: UUID,
    body: SampleUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    sample_svc: Annotated[SampleService, Depends(sample_service_dependency)],
):
    """draft 상태 샘플의 제목·내용을 수정한다."""
    sample = await sample_svc.update_content(
        sample_id=sample_id,
        title=body.title or "",
        content=body.content or "",
    )
    return SampleResponse.from_domain(sample)


@router.post("/samples/{sample_id}/publish", response_model=SampleResponse)
async def publish_sample(
    sample_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    sample_svc: Annotated[SampleService, Depends(sample_service_dependency)],
):
    """샘플을 published 상태로 전이한다."""
    sample = await sample_svc.publish(sample_id)
    return SampleResponse.from_domain(sample)


@router.post("/samples/{sample_id}/archive", response_model=SampleResponse)
async def archive_sample(
    sample_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    sample_svc: Annotated[SampleService, Depends(sample_service_dependency)],
):
    """샘플을 archived 상태로 전이한다."""
    sample = await sample_svc.archive(sample_id)
    return SampleResponse.from_domain(sample)
