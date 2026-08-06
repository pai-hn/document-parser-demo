"""애플리케이션 최상위 DI 컨테이너.

모든 도메인 컨테이너를 조합하여 의존성 그래프를 구성합니다.
``WiringConfiguration``을 통해 ``webapp`` 패키지의 모든 모듈에
자동으로 의존성이 주입됩니다.

의존성 흐름 (Level 순서)::

    L0: DatabaseContainer (인프라)
    L1: UserContainer, SampleContainer (단일 도메인)
    L2: AuthContainer (교차 도메인 — User에 의존)
"""

from dependency_injector import containers, providers

from src.auth.container import AuthContainer
from src.document.container import DocumentContainer
from src.sample.container import SampleContainer
from src.storages.database.container import DatabaseContainer
from src.user.container import UserContainer


class ApplicationContainer(containers.DeclarativeContainer):
    """애플리케이션 전체의 의존성 주입 루트 컨테이너."""

    wiring_config = containers.WiringConfiguration(packages=["webapp"])
    database = providers.Container(DatabaseContainer)
    user = providers.Container(UserContainer, database=database)
    auth = providers.Container(AuthContainer, user_repo=user.user_repo)
    sample = providers.Container(SampleContainer, database=database)
    document = providers.Container(DocumentContainer)


def create_container() -> ApplicationContainer:
    """기본 설정으로 ApplicationContainer를 생성한다."""
    container = ApplicationContainer()
    return container
