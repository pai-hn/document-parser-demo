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



# --- Health DTO ---


class HealthResponse(CommonModel):
    """헬스체크 응답."""

    status: str
    services: dict[str, str] | None = None
