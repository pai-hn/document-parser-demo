"""데이터베이스 계층의 의존성 주입 컨테이너.

``DatabaseSettings``와 ``SessionFactory``를 싱글톤으로 제공하며,
상위 컨테이너(``ApplicationContainer``)에서 주입받아 사용합니다.
"""

from dependency_injector import containers, providers

from src.storages.database.session_factory import SessionFactory
from src.storages.database.settings import DatabaseSettings


class DatabaseContainer(containers.DeclarativeContainer):
    settings = providers.Singleton(DatabaseSettings)

    session_factory = providers.Singleton(SessionFactory, settings=settings)
