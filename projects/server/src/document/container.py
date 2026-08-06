"""Document 도메인 DI 컨테이너."""

from dependency_injector import containers, providers

from src.document.service import DocumentService


class DocumentContainer(containers.DeclarativeContainer):
    """Document Detection 서비스 컨테이너 (인프라 의존 없음)."""

    service = providers.Singleton(DocumentService)
