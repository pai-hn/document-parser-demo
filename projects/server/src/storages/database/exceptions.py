"""데이터베이스 계층 전용 예외.

공통 애플리케이션 예외를 래핑하여, 저장소 계층의 호출자가
SQLAlchemy 세부사항에 의존하지 않고 의미에 맞는 예외를 처리할 수 있게 합니다.
"""

from src.common.exceptions import (
    ConflictException,
    ServerException,
)
from src.common.exceptions import (
    NotFoundException as CommonNotFoundException,
)


class DatabaseException(ServerException):
    """데이터베이스 레벨 오류."""

    error_code = "DATABASE_ERROR"


class NotFoundException(CommonNotFoundException):
    """요청한 레코드가 데이터베이스에 존재하지 않음."""


class AlreadyExistsException(ConflictException):
    """이미 존재하는 레코드 (유니크 제약 위반)."""

    error_code = "ALREADY_EXISTS"


class DBIntegrityException(DatabaseException):
    """데이터베이스 무결성 제약 위반."""

    error_code = "DB_INTEGRITY_ERROR"
