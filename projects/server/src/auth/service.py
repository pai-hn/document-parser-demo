"""JWT 기반 인증 서비스.

로그인, 토큰 생성·검증·갱신, 현재 사용자 조회를 담당합니다.
PyJWT 라이브러리를 사용하며, ``AuthSettings``에서 서명 알고리즘과
시크릿 키를 읽어옵니다.

토큰 구조::

    Access Token  — 사용자 클레임 포함, 단기 유효 (기본 1일)
    Refresh Token — 최소 클레임, 장기 유효 (기본 7일)
"""

import logging
from datetime import timedelta
from uuid import UUID

import jwt

from src.auth.settings import AuthSettings
from src.common.exceptions import UnauthorizedException
from src.user.domains import User
from src.user.password import verify_password
from src.user.repository import UserRepository
from src.utils import utc_now

logger = logging.getLogger(__name__)


class AuthService:
    """JWT 인증을 처리하는 서비스: 로그인, 토큰 갱신, 사용자 식별."""

    def __init__(self, user_repo: UserRepository, settings: AuthSettings):
        self._user_repo = user_repo
        self._settings = settings

    # -- 토큰 생성·검증 --

    def _create_access_token(self, user: User) -> str:
        """사용자 클레임이 포함된 단기 Access JWT를 생성한다."""
        now = utc_now()
        expire = now + timedelta(minutes=self._settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(user.user_id),
            "username": user.username,
            "role": user.role,
            "team_id": str(user.team_id) if user.team_id else None,
            "must_change_password": user.must_change_password,
            "type": "access",
            "iat": now,
            "exp": expire,
        }
        return jwt.encode(
            payload,
            self._settings.JWT_SECRET_KEY,
            algorithm=self._settings.JWT_ALGORITHM,
        )

    def _create_refresh_token(self, user: User) -> str:
        """최소 클레임의 장기 Refresh JWT를 생성한다."""
        now = utc_now()
        expire = now + timedelta(days=self._settings.REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": str(user.user_id),
            "type": "refresh",
            "iat": now,
            "exp": expire,
        }
        return jwt.encode(
            payload,
            self._settings.JWT_SECRET_KEY,
            algorithm=self._settings.JWT_ALGORITHM,
        )

    def _decode_token(self, token: str) -> dict:
        """JWT를 디코딩하고 유효성을 검증한다.

        Args:
            token: JWT 문자열.

        Returns:
            디코딩된 페이로드 딕셔너리.

        Raises:
            UnauthorizedException: 토큰이 유효하지 않거나 만료되었을 때.
        """
        try:
            return jwt.decode(
                token,
                self._settings.JWT_SECRET_KEY,
                algorithms=[self._settings.JWT_ALGORITHM],
            )
        except jwt.PyJWTError as e:
            raise UnauthorizedException(f"Invalid or expired token: {e}") from e

    # -- 공개 API --

    async def login(self, username: str, password: str) -> tuple[str, str] | None:
        """사용자를 인증하고 토큰 쌍을 반환한다.

        Args:
            username: 로그인 아이디.
            password: 평문 비밀번호.

        Returns:
            (access_token, refresh_token) 튜플. 인증 실패 시 None.
        """
        user = await self._user_repo.find_by_username(username)
        if user is None:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        user.last_login_at = utc_now()
        await self._user_repo.update(user)
        access_token = self._create_access_token(user)
        refresh_token = self._create_refresh_token(user)
        return access_token, refresh_token

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """유효한 Refresh Token으로 새 토큰 쌍을 발급한다.

        Args:
            refresh_token: 기존 Refresh JWT.

        Returns:
            (새 access_token, 새 refresh_token) 튜플.

        Raises:
            UnauthorizedException: 토큰이 유효하지 않거나 타입이 refresh가 아닐 때.
        """
        payload = self._decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Invalid token type: expected refresh token")
        user_id = UUID(payload["sub"])
        user = await self._user_repo.get_by_id(user_id)
        access_token = self._create_access_token(user)
        new_refresh_token = self._create_refresh_token(user)
        return access_token, new_refresh_token

    def get_user_id_from_token(self, token: str) -> UUID | None:
        """Access Token에서 user_id를 추출한다 (DB 조회 없음).

        Args:
            token: Access JWT 문자열.

        Returns:
            사용자 UUID. 토큰이 유효하지 않거나 access 타입이 아니면 None.
        """
        try:
            payload = self._decode_token(token)
        except UnauthorizedException:
            return None
        if payload.get("type") != "access":
            return None
        try:
            return UUID(payload["sub"])
        except (KeyError, ValueError):
            return None

    async def get_current_user(self, token: str) -> User:
        """Access Token에서 사용자를 식별하고 전체 User 도메인 객체를 반환한다.

        Args:
            token: Access JWT 문자열.

        Returns:
            현재 인증된 User 도메인 객체.

        Raises:
            UnauthorizedException: 토큰이 유효하지 않거나 access 타입이 아닐 때.
        """
        payload = self._decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type: expected access token")
        user_id = UUID(payload["sub"])
        return await self._user_repo.get_by_id(user_id)
