"""테스트 공유 픽스처.

통합 테스트 실행 시 testcontainers를 통해 일회용 PostgreSQL 컨테이너를 띄우고,
테스트 세션 동안 유지합니다. 각 테스트 함수는 트랜잭션 내에서 실행되며,
테스트 종료 시 자동으로 롤백되어 테스트 간 격리를 보장합니다.

Usage::

    async def test_something():
        assert True

    async def test_with_db(session):
        result = await session.execute(select(UserEntity))
        ...
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from src.storages.database.base import Base
from src.storages.database.settings import DatabaseSettings


@pytest.fixture(scope="session")
def event_loop():
    """테스트 세션 전체에서 공유하는 이벤트 루프를 제공한다."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def pytest_collection_modifyitems(items):
    """비동기 테스트 함수에 자동으로 asyncio 마커를 적용한다."""
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


@pytest.fixture(scope="session")
def postgres_container():
    """테스트 세션 동안 일회용 PostgreSQL 컨테이너를 실행한다."""
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_settings(postgres_container) -> DatabaseSettings:
    """테스트 컨테이너의 접속 정보로 DatabaseSettings를 생성한다."""
    return DatabaseSettings(
        DB_NAME=postgres_container.dbname,
        DB_USER=postgres_container.username,
        DB_PASSWORD=postgres_container.password,
        DB_HOST=postgres_container.get_container_host_ip(),
        DB_PORT=int(postgres_container.get_exposed_port(5432)),
    )


@pytest.fixture(scope="session")
def session_factory(db_settings, event_loop):
    """테스트 데이터베이스에 바인딩된 비동기 세션 팩토리를 생성한다."""
    url = (
        f"postgresql+asyncpg://{db_settings.DB_USER}:{db_settings.DB_PASSWORD}"
        f"@{db_settings.DB_HOST}:{db_settings.DB_PORT}/{db_settings.DB_NAME}"
    )
    engine = create_async_engine(url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    event_loop.run_until_complete(_init())

    yield factory

    async def _teardown():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    event_loop.run_until_complete(_teardown())


@pytest.fixture
async def session(session_factory) -> AsyncSession:
    """각 테스트에 트랜잭셔널 DB 세션을 제공하고, 종료 시 롤백한다."""
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="session")
def initialize_database(session_factory):
    """데이터베이스 스키마가 준비되었음을 보장하는 마커 픽스처."""
    return session_factory
