"""애플리케이션 예외 계층 구조.

모든 애플리케이션 오류는 ``AppException``을 상속하며,
클라이언트 오류(4xx)는 ``ClientException``, 서버 오류(5xx)는 ``ServerException``을
각각 기반 클래스로 사용합니다.

각 예외 클래스는 고정된 ``error_code``를 가지며, API 에러 응답에서 일관된 코드로 활용됩니다.

Usage::

    from src.common.exceptions import NotFoundException, BadRequestException

    raise NotFoundException("사용자를 찾을 수 없습니다")
    raise BadRequestException("비밀번호가 올바르지 않습니다", detail={"field": "password"})
"""

from typing import Any


class AppException(Exception):
    """모든 애플리케이션 예외의 최상위 클래스.

    Attributes:
        status_code: HTTP 상태 코드.
        error_code: API 응답에 포함되는 고유 에러 코드 문자열.
        message: 사람이 읽을 수 있는 오류 메시지.
        detail: 추가 상세 정보 (선택).
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: Any = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


# --- 클라이언트 오류 (4xx) ---


class ClientException(AppException):
    """4xx 계열 클라이언트 오류의 기반 클래스."""

    status_code = 400
    error_code = "BAD_REQUEST"


class BadRequestException(ClientException):
    """400 — 잘못된 입력 또는 비즈니스 규칙 위반."""

    status_code = 400
    error_code = "BAD_REQUEST"


class UnauthorizedException(ClientException):
    """401 — 인증 실패 (토큰 없음·만료·잘못됨)."""

    status_code = 401
    error_code = "UNAUTHORIZED"


class ForbiddenException(ClientException):
    """403 — 권한 부족."""

    status_code = 403
    error_code = "FORBIDDEN"


class NotFoundException(ClientException):
    """404 — 요청한 리소스를 찾을 수 없음."""

    status_code = 404
    error_code = "NOT_FOUND"


class ConflictException(ClientException):
    """409 — 리소스 중복 또는 상태 충돌."""

    status_code = 409
    error_code = "CONFLICT"


class InvalidStateException(ClientException):
    """422 — 현재 상태에서 허용되지 않는 작업 (상태 머신 위반)."""

    status_code = 422
    error_code = "INVALID_STATE"


# --- 서버 오류 (5xx) ---


class ServerException(AppException):
    """5xx 계열 서버 오류의 기반 클래스."""

    status_code = 500
    error_code = "INTERNAL_ERROR"
