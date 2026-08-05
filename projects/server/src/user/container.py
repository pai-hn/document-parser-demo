"""User 도메인의 의존성 주입 컨테이너.

``database`` 컨테이너로부터 ``session_factory``를 주입받아
``UserRepository`` → ``UserService`` 의존성 체인을 구성합니다.
"""

from dependency_injector import containers, providers

from src.user.repository import UserRepository
from src.user.service import UserService


class UserContainer(containers.DeclarativeContainer):
    database = providers.DependenciesContainer()

    user_repo = providers.Singleton(UserRepository, session_factory=database.session_factory)
    service = providers.Singleton(UserService, user_repo=user_repo)
