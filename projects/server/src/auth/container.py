"""Auth 도메인의 의존성 주입 컨테이너.

``UserRepository``를 외부에서 주입받아 ``AuthService``에 전달합니다.
Auth는 User 도메인에 의존하는 L2 계층이므로, user_repo를 Dependency()로 선언합니다.
"""

from dependency_injector import containers, providers

from src.auth.service import AuthService
from src.auth.settings import AuthSettings


class AuthContainer(containers.DeclarativeContainer):
    user_repo = providers.Dependency()

    settings = providers.Singleton(AuthSettings)
    service = providers.Singleton(AuthService, user_repo=user_repo, settings=settings)
