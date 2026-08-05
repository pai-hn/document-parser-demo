"""인증 엔드포인트 — 로그인 및 토큰 갱신."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.service import AuthService
from webapp.dependency import auth_service_dependency
from webapp.dto import LoginRequest, RefreshRequest, TokenResponse

router = APIRouter()


@router.post("/auth/token", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth_svc: Annotated[AuthService, Depends(auth_service_dependency)],
):
    """아이디·비밀번호로 로그인하여 JWT 토큰 쌍을 발급한다."""
    result = await auth_svc.login(body.username, body.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    access_token, refresh_token = result
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    auth_svc: Annotated[AuthService, Depends(auth_service_dependency)],
):
    """Refresh Token으로 새 토큰 쌍을 발급한다."""
    access_token, refresh_token = await auth_svc.refresh(body.refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
