"""Document 도메인 DI 컨테이너."""

from dependency_injector import containers, providers

from src.document.pipeline.engine import LayoutOcrPipeline
from src.document.service import DocumentService
from src.document.settings import DocumentSettings


class DocumentContainer(containers.DeclarativeContainer):
    """Document Detection 서비스 컨테이너."""

    settings = providers.Singleton(DocumentSettings)
    pipeline = providers.Singleton(LayoutOcrPipeline, settings=settings)
    service = providers.Singleton(DocumentService, pipeline=pipeline, settings=settings)
