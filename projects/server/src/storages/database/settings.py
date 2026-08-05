"""데이터베이스 접속 설정.

환경 변수 또는 ``.env`` 파일에서 접속 정보를 읽어옵니다.
pydantic-settings를 사용하므로 타입 검증이 자동으로 적용됩니다.

필수 환경 변수::

    DB_NAME=my_database
    DB_USER=postgres
    DB_PASSWORD=secret

선택 환경 변수 (기본값 있음)::

    DB_HOST=localhost     # 기본값: localhost
    DB_PORT=5432          # 기본값: 5432
    DB_ECHO=false         # SQL 로깅 여부
    DB_POOL_SIZE=5        # 커넥션 풀 크기
    DB_MAX_OVERFLOW=10    # 풀 초과 허용 커넥션 수
    DB_POOL_RECYCLE=3600  # 커넥션 재활용 주기 (초)
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL 접속 설정."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DB_NAME: str = Field()
    DB_USER: str = Field()
    DB_PASSWORD: str = Field()
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_ECHO: bool = Field(default=False)
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)
    DB_POOL_RECYCLE: int = Field(default=3600)
