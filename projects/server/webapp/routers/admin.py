"""관리자 전용 엔드포인트 — 사용자 CRUD + 팀 멤버 관리.

권한 체계:
- master: 전체 사용자 CRUD, 활성/비활성, 비밀번호 초기화
- admin: 본인 팀 멤버 추가/비활성화/비밀번호 초기화
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.user.domains import User
from src.user.service import UserService
from src.utils import utc_now
from webapp.dependency import require_min_role, require_role, user_service_dependency
from webapp.dto import CreateUserRequest, ResetPasswordRequest, UserResponse

router = APIRouter(prefix="/admin")


# ── 헬퍼 ─────────────────────────────────────────────────────────────


def _get_team_id(user: User) -> UUID:
    """admin/master의 팀 ID를 반환한다. admin은 team_id, master는 user_id."""
    return user.team_id or user.user_id


async def _get_team_member(user_svc: UserService, user_id: UUID, team_id: UUID) -> User:
    """팀 멤버를 조회하고 소속 팀을 검증한다."""
    user = await user_svc.get_user(user_id)
    if user.team_id != team_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your team member")
    return user


async def _toggle_active(user: User, *, activate: bool, user_svc: UserService) -> UserResponse:
    """사용자의 활성/비활성 상태를 전환한다."""
    if activate:
        user.activate(updated_at=utc_now())
    else:
        user.deactivate(updated_at=utc_now())
    await user_svc.update_user(user)
    return UserResponse.from_domain(user)


# ── Master: 전체 사용자 관리 ──────────────────────────────────────────


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(require_role("master"))],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """전체 사용자 목록을 반환한다."""
    users = await user_svc.find_all()
    return [UserResponse.from_domain(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    current_user: Annotated[User, Depends(require_role("master"))],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """새 사용자를 생성한다. admin 생성 시 team_id를 자동 배정한다."""
    created = await user_svc.create_user(
        username=body.username,
        password=body.password,
        role=body.role or "member",
        display_name=body.display_name,
    )
    if created.role == "admin":
        created.assign_team(team_id=created.user_id, updated_at=utc_now())
        await user_svc.update_user(created)
    return UserResponse.from_domain(created)


@router.put("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_role("master"))],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """사용자를 비활성화한다."""
    user = await user_svc.get_user(user_id)
    return await _toggle_active(user, activate=False, user_svc=user_svc)


@router.put("/users/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_role("master"))],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """사용자를 활성화한다."""
    user = await user_svc.get_user(user_id)
    return await _toggle_active(user, activate=True, user_svc=user_svc)


@router.put("/users/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_password(
    user_id: UUID,
    body: ResetPasswordRequest,
    current_user: Annotated[User, Depends(require_role("master"))],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """사용자의 비밀번호를 초기화한다."""
    await user_svc.admin_reset_password(user_id, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Admin: 본인 팀 멤버 관리 ──────────────────────────────────────────


@router.get("/team/members", response_model=list[UserResponse])
async def list_team_members(
    current_user: Annotated[User, Depends(require_min_role("admin"))],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """본인 팀의 멤버 목록을 반환한다."""
    members = await user_svc.find_by_team_id(_get_team_id(current_user))
    return [UserResponse.from_domain(m) for m in members]


@router.post("/team/members", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_team_member(
    body: CreateUserRequest,
    current_user: Annotated[User, Depends(require_min_role("admin"))],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """본인 팀에 멤버를 추가한다."""
    return UserResponse.from_domain(
        await user_svc.create_user(
            username=body.username,
            password=body.password,
            role="member",
            display_name=body.display_name,
            team_id=_get_team_id(current_user),
        )
    )


@router.put("/team/members/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_team_member(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_min_role("admin"))],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """팀 멤버를 비활성화한다."""
    user = await _get_team_member(user_svc, user_id, _get_team_id(current_user))
    return await _toggle_active(user, activate=False, user_svc=user_svc)


@router.put("/team/members/{user_id}/activate", response_model=UserResponse)
async def activate_team_member(
    user_id: UUID,
    current_user: Annotated[User, Depends(require_min_role("admin"))],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """팀 멤버를 활성화한다."""
    user = await _get_team_member(user_svc, user_id, _get_team_id(current_user))
    return await _toggle_active(user, activate=True, user_svc=user_svc)


@router.put("/team/members/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_team_member_password(
    user_id: UUID,
    body: ResetPasswordRequest,
    current_user: Annotated[User, Depends(require_min_role("admin"))],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """팀 멤버의 비밀번호를 초기화한다."""
    await _get_team_member(user_svc, user_id, _get_team_id(current_user))
    await user_svc.admin_reset_password(user_id, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
