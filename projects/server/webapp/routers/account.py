"""계정 엔드포인트 — 내 정보 조회 및 비밀번호 변경."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from src.user.domains import User
from src.user.service import UserService
from webapp.dependency import get_current_user, user_service_dependency
from webapp.dto import ChangePasswordRequest, UserResponse

router = APIRouter()


@router.get("/account/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """현재 로그인된 사용자의 정보를 반환한다."""
    return UserResponse.from_domain(current_user)


@router.put("/account/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    user_svc: Annotated[UserService, Depends(user_service_dependency)],
):
    """현재 비밀번호를 확인한 뒤 새 비밀번호로 변경한다."""
    await user_svc.change_password(
        user_id=current_user.user_id,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
