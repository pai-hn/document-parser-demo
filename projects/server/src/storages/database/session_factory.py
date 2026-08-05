"""비동기 SQLAlchemy 세션 팩토리.

``SessionFactory``는 데이터베이스 세션 관리의 단일 진입점입니다.
``AsyncEngine``을 한 번 생성하고, async context manager ``__call__``을 통해
적절히 스코핑된 ``AsyncSession``을 제공합니다.

세션은 asyncio task 단위로 스코핑되어 하나의 요청 내에서 같은 세션을 공유합니다.
예외 발생 시 자동으로 롤백되며, 항상 세션이 정리(close + remove)됩니다.

Usage::

    session_factory = SessionFactory(settings)

    async with session_factory() as session:
        result = await session.execute(select(UserEntity))
        # 예외 발생 시 자동 롤백
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager, asynccontextmanager

import sqlalchemy.exc
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from src.storages.database.base import Base
from src.storages.database.exceptions import (
    DBIntegrityException,
    NotFoundException,
)
from src.storages.database.settings import DatabaseSettings

logger = logging.getLogger(__name__)


class SessionFactory:
    """비동기 세션 팩토리 (QueuePool 커넥션 풀링 + asyncio task 스코프).

    Args:
        settings: 데이터베이스 접속 정보를 담은 설정 객체.
    """

    def __init__(self, settings: DatabaseSettings):
        url = URL.create(
            "postgresql+asyncpg",
            username=settings.DB_USER,
            password=settings.DB_PASSWORD,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
        )
        self._engine = create_async_engine(
            url,
            echo=settings.DB_ECHO,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=True,
            connect_args={"timeout": 5},
        )

        self._session_factory = async_scoped_session(
            async_sessionmaker(
                autocommit=False,
                bind=self._engine,
            ),
            scopefunc=asyncio.current_task,
        )

    async def create_database(self) -> None:
        """ORM 메타데이터 기반으로 모든 테이블을 생성한다 (개발·테스트 용도)."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_database(self) -> None:
        """모든 테이블을 삭제한다 (테스트 정리 용도)."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager  # type: ignore
    async def __call__(self) -> Callable[..., AbstractContextManager[AsyncSession]]:  # type: ignore
        """스코핑된 AsyncSession을 yield하는 비동기 컨텍스트 매니저.

        Yields:
            현재 asyncio task에 바인딩된 AsyncSession.

        Raises:
            NotFoundException: ``NoResultFound`` 발생 시 도메인 예외로 변환.
            DBIntegrityException: ``IntegrityError`` 발생 시 도메인 예외로 변환.
        """
        session: AsyncSession = self._session_factory()
        try:
            yield session  # type: ignore
        except sqlalchemy.exc.NoResultFound:
            await session.rollback()
            raise NotFoundException("Requested record was not found.")
        except sqlalchemy.exc.IntegrityError:
            await session.rollback()
            raise DBIntegrityException("Database integrity constraint violation.")
        except Exception as e:
            logger.exception("Session rollback because of exception")
            await session.rollback()
            raise e
        finally:
            await session.close()
            await self._session_factory.remove()
