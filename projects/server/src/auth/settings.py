"""인증 설정.

환경 변수 또는 ``.env`` 파일에서 JWT 관련 설정을 읽어옵니다.

필수 환경 변수::

    JWT_SECRET_KEY=your-secret-key

선택 환경 변수 (기본값 있음)::

    JWT_ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=1440   # 1일
    REFRESH_TOKEN_EXPIRE_DAYS=7
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """JWT 인증 설정."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    JWT_SECRET_KEY: str = Field(description="JWT 서명에 사용하는 시크릿 키")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT 서명 알고리즘")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="Access Token 유효 시간 (분, 기본 1일)")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh Token 유효 기간 (일)")
