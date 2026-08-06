"""요청/응답 DTO (Data Transfer Object) 정의.

모든 DTO는 ``CommonModel``을 상속하며, ``alias_generator=to_camel``을 통해
JSON 필드명이 자동으로 camelCase로 변환됩니다.

규칙:
    - Python 코드에서는 snake_case (``user_id``)
    - JSON 직렬화 시에는 camelCase (``userId``)
    - ``populate_by_name=True``이므로 양쪽 모두 역직렬화 가능
"""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    """snake_case 문자열을 camelCase로 변환한다."""
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CommonModel(BaseModel):
    """모든 DTO의 기반 클래스."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    @classmethod
    def from_domain(cls, domain) -> Self:
        """도메인 객체를 응답 DTO로 변환한다."""
        return cls.model_validate(domain, from_attributes=True)


# --- Auth DTO ---


class LoginRequest(CommonModel):
    """로그인 요청."""

    username: str
    password: str


class TokenResponse(CommonModel):
    """토큰 응답 (access + refresh)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(CommonModel):
    """토큰 갱신 요청."""

    refresh_token: str


# --- Account DTO ---


class ChangePasswordRequest(CommonModel):
    """비밀번호 변경 요청."""

    current_password: str
    new_password: str


class UpdateProfileRequest(CommonModel):
    """프로필 수정 요청."""

    display_name: str | None = None


class CreateUserRequest(CommonModel):
    """사용자 생성 요청 (관리자용)."""

    username: str
    password: str
    display_name: str | None = None
    role: str = "member"


class ResetPasswordRequest(CommonModel):
    """비밀번호 초기화 요청 (관리자용)."""

    new_password: str


class UserResponse(CommonModel):
    """사용자 응답."""

    user_id: UUID
    username: str
    display_name: str | None
    role: str
    team_id: UUID | None
    github_username: str | None
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


# --- Sample DTO ---


class SampleCreateRequest(CommonModel):
    """샘플 생성 요청."""

    title: str
    content: str | None = None


class SampleUpdateRequest(CommonModel):
    """샘플 수정 요청."""

    title: str | None = None
    content: str | None = None


class SampleResponse(CommonModel):
    """샘플 응답."""

    sample_id: UUID
    title: str
    content: str
    status: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime


# --- Document Detection DTO ---


class BBoxResponse(CommonModel):
    """정규화된 바운딩 박스."""

    x: float
    y: float
    w: float
    h: float


class DetectionBlockResponse(CommonModel):
    """Detection 블록."""

    id: str
    index: int
    page: int
    type: str
    bbox: BBoxResponse
    markdown: str
    html: str = ""
    # Vision 검증용 정규화 좌표 [x1,y1,x2,y2]
    bbox_xyxy: list[float] | None = None


class DocumentPageResponse(CommonModel):
    """문서 페이지."""

    page_number: int
    width: int
    height: int
    image_url: str
    blocks: list[DetectionBlockResponse]


class DetectionResultResponse(CommonModel):
    """문서 Detection 결과 (멀티 페이지)."""

    document_id: UUID
    filename: str
    page_count: int
    page_width: int
    page_height: int
    image_url: str
    pages: list[DocumentPageResponse]
    blocks: list[DetectionBlockResponse]

    @classmethod
    def from_domain(cls, domain) -> Self:
        """도메인 DetectionResult를 응답 DTO로 변환한다."""
        pages: list[DocumentPageResponse] = []
        for page in domain.pages:
            page_blocks = [
                DetectionBlockResponse(
                    id=b.id,
                    index=b.index,
                    page=b.page,
                    type=b.type,
                    bbox=BBoxResponse(x=b.bbox.x, y=b.bbox.y, w=b.bbox.w, h=b.bbox.h),
                    markdown=b.markdown,
                    html=getattr(b, "html", "") or "",
                    bbox_xyxy=b.bbox.to_xyxy(),
                )
                for b in page.blocks
            ]
            pages.append(
                DocumentPageResponse(
                    page_number=page.page_number,
                    width=page.width,
                    height=page.height,
                    image_url=page.image_url_for(domain.document_id),
                    blocks=page_blocks,
                )
            )
        all_blocks = [block for page in pages for block in page.blocks]
        return cls(
            document_id=domain.document_id,
            filename=domain.filename,
            page_count=domain.page_count,
            page_width=domain.page_width,
            page_height=domain.page_height,
            image_url=domain.image_url,
            pages=pages,
            blocks=all_blocks,
        )


class SampleProjectResponse(CommonModel):
    """샘플 프로젝트 목록 항목."""

    sample_id: str
    title: str
    file_count: int
    thumbnail_url: str

    @classmethod
    def from_domain(cls, domain) -> Self:
        """샘플 도메인을 응답 DTO로 변환한다."""
        return cls(
            sample_id=domain.sample_id,
            title=domain.title,
            file_count=domain.file_count,
            thumbnail_url=f"/documents/samples/{domain.sample_id}/thumbnail",
        )


# --- Health DTO ---


class HealthResponse(CommonModel):
    """헬스체크 응답."""

    status: str
    services: dict[str, str] | None = None
