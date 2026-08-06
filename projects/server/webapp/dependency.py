"""FastAPI Depends() 함수 — dependency-injector와 FastAPI DI를 연결합니다.

각 ``*_dependency`` 함수는 DI 컨테이너에서 서비스를 꺼내 FastAPI에 주입합니다.
인증이 필요한 엔드포인트에서는 ``get_current_user``를, 역할 제한이 필요하면
``require_min_role("admin")`` 또는 ``require_role("master")``를 사용합니다.

Usage::

    @router.get("/samples")
    async def list_samples(
        sample_svc: Annotated[SampleService, Depends(sample_service_dependency)],
    ):
        return await sample_svc.find_all()

    @router.post("/admin/users")
    async def create_user(
        current_user: Annotated[User, Depends(require_min_role("admin"))],
        user_svc: Annotated[UserService, Depends(user_service_dependency)],
    ):
        ...
"""

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.service import AuthService
from src.common.exceptions import AppException
from src.document.service import DocumentService
from src.sample.service import SampleService
from src.user.domains import User
from src.user.service import UserService
from webapp.container import ApplicationContainer

bearer_scheme = HTTPBearer()


@inject
async def auth_service_dependency(
    service: AuthService = Depends(Provide[ApplicationContainer.auth.service]),
) -> AuthService:
    """AuthService를 DI 컨테이너에서 주입받는다."""
    return service


@inject
async def user_service_dependency(
    service: UserService = Depends(Provide[ApplicationContainer.user.service]),
) -> UserService:
    """UserService를 DI 컨테이너에서 주입받는다."""
    return service


@inject
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    auth_service: AuthService = Depends(Provide[ApplicationContainer.auth.service]),
) -> User:
    """Bearer 토큰에서 현재 인증된 사용자를 추출한다."""
    try:
        user = await auth_service.get_current_user(credentials.credentials)
    except AppException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    return user


def require_min_role(min_role: str):
    """최소 역할 레벨을 요구하는 의존성 팩토리."""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.has_min_role(min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Minimum role '{min_role}' required",
            )
        return current_user

    return dependency


def require_role(role: str):
    """정확한 역할 일치를 요구하는 의존성 팩토리."""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{role}' required")
        return current_user

    return dependency


@inject
async def sample_service_dependency(
    service: SampleService = Depends(Provide[ApplicationContainer.sample.service]),
) -> SampleService:
    """SampleService를 DI 컨테이너에서 주입받는다."""
    return service


@inject
async def document_service_dependency(
    service: DocumentService = Depends(Provide[ApplicationContainer.document.service]),
) -> DocumentService:
    """DocumentService를 DI 컨테이너에서 주입받는다."""
    return service
