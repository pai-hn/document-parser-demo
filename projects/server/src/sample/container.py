"""Sample 도메인의 의존성 주입 컨테이너.

``database`` 컨테이너로부터 ``session_factory``를 주입받아
``SampleRepository`` → ``SampleService`` 의존성 체인을 구성합니다.
"""

from dependency_injector import containers, providers

from src.sample.repository import SampleRepository
from src.sample.service import SampleService


class SampleContainer(containers.DeclarativeContainer):
    database = providers.DependenciesContainer()

    sample_repo = providers.Singleton(SampleRepository, session_factory=database.session_factory)
    service = providers.Singleton(SampleService, sample_repo=sample_repo)
