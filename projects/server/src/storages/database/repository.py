"""제네릭 비동기 CRUD 레포지토리.

``BaseRepository[DomainKey, Domain]``는 엔티티-도메인 자동 매핑을 기반으로
create, update, upsert(save), delete 및 다양한 조회 메서드를 제공합니다.

새 도메인을 추가할 때 레포지토리 서브클래스에서는 ``entity`` 클래스 변수만
지정하면 기본 CRUD가 모두 동작하며, 도메인별 커스텀 쿼리만 추가하면 됩니다.
관계(relationship) 기반 eager loading도 자동으로 처리됩니다.

Usage::

    class SampleRepository(BaseRepository[UUID, Sample]):
        entity: type[SampleEntity] = SampleEntity

        async def find_by_status(self, status: str) -> list[Sample]:
            async with self.session_factory() as session:
                stmt = select(SampleEntity).where(SampleEntity.status == status)
                result = await session.execute(stmt)
                return [e.to_domain() for e in result.scalars().all()]
"""

import abc
import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import fields
from typing import Generic

from sqlalchemy import delete, exists, func, inspect, select, update
from sqlalchemy.exc import DataError, IntegrityError, NoResultFound, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.storages.database.base import Base, Domain, DomainKey
from src.storages.database.exceptions import AlreadyExistsException, NotFoundException

logger = logging.getLogger(__name__)


def reflect_domain(src, dst):
    """flush 후 DB가 생성한 값(기본 키, 타임스탬프 등)을 원본 도메인 객체에 동기화한다.

    Args:
        src: 값을 덮어쓸 대상 도메인 객체 (호출자가 들고 있는 원본).
        dst: flush 이후 엔티티에서 변환된 새 도메인 객체.
    """
    for field in fields(dst):
        new_value = getattr(dst, field.name)
        setattr(src, field.name, new_value)


class BaseRepository(abc.ABC, Generic[DomainKey, Domain]):
    """모든 도메인 레포지토리의 기반 클래스.

    서브클래스에서 ``entity`` 클래스 변수에 ORM 엔티티 타입을 지정하면
    create, update, delete, find_by 등 기본 CRUD 메서드를 바로 사용할 수 있습니다.
    관계(relationship)가 있는 엔티티는 자동으로 joinedload가 적용됩니다.

    Attributes:
        entity: 이 레포지토리가 관리하는 ORM 엔티티 클래스.
    """

    entity: Base

    def __init__(self, session_factory: Callable[..., AbstractContextManager[AsyncSession]]):
        logger.info(f"initialize Repository({self.entity.__name__})")
        self.session_factory = session_factory

    # ---- 쓰기 작업 ----

    async def create(self, domain: Domain) -> None:
        """도메인 객체를 새 레코드로 저장한다.

        Args:
            domain: 저장할 도메인 객체. flush 후 DB 생성 값이 이 객체에 반영된다.

        Raises:
            AlreadyExistsException: 유니크 제약 위반 시.
        """
        async with self.session_factory() as session:  # type: ignore
            await self._create(session, domain)
            await session.commit()

    async def update(self, domain: Domain) -> None:
        """기존 레코드를 도메인 객체의 현재 상태로 갱신한다.

        Args:
            domain: 변경된 도메인 객체.

        Raises:
            NotFoundException: 해당 기본 키의 레코드가 없을 때.
        """
        async with self.session_factory() as session:  # type: ignore
            entity_primary_key = get_primary_key(self.entity, domain)
            try:
                entity = await self._get_by_id(session, entity_primary_key)
            except NotFoundException:
                raise NotFoundException(f"{self.entity} with key {entity_primary_key} not found.")
            await self._update(session, entity, domain)
            await session.commit()

    async def update_field(self, key: DomainKey, **kwargs) -> bool:
        """특정 필드만 부분 업데이트한다.

        Args:
            key: 대상 레코드의 기본 키.
            **kwargs: 업데이트할 필드명=값 쌍.

        Returns:
            업데이트된 행이 있으면 True.
        """
        async with self.session_factory() as session:  # type: ignore
            criteria = create_id_criteria(self.entity, key)
            result = await session.execute(
                update(self.entity).filter(*criteria).values(**kwargs)  # type: ignore
            )
            await session.commit()
            return result.rowcount > 0

    async def save(self, domain: Domain) -> None:
        """Upsert: 존재하면 갱신, 없으면 새로 생성한다.

        Args:
            domain: 저장할 도메인 객체.
        """
        async with self.session_factory() as session:  # type: ignore
            entity_primary_key = get_primary_key(self.entity, domain)
            if entity := await self._find_by_id(session, entity_primary_key):
                await self._update(session, entity, domain)
            else:
                await self._create(session, domain)
            await session.commit()

    async def delete(self, key: DomainKey) -> None:
        """기본 키로 레코드를 삭제한다.

        Args:
            key: 삭제할 레코드의 기본 키.

        Raises:
            NotFoundException: 해당 레코드가 없을 때.
        """
        async with self.session_factory() as session:  # type: ignore
            criteria = create_id_criteria(self.entity, key)
            stmt = delete(self.entity).filter(*criteria)  # type: ignore
            if (await session.execute(stmt)).rowcount == 0:
                raise NotFoundException(f"{self.entity} with key {key} not found.")
            await session.commit()

    async def delete_by(self, **kwargs) -> None:
        """조건에 맞는 레코드를 모두 삭제한다.

        Args:
            **kwargs: 필터 조건 (필드명=값).
        """
        async with self.session_factory() as session:  # type: ignore
            criteria = create_field_criteria(self.entity, kwargs)
            stmt = delete(self.entity).filter(*criteria)  # type: ignore
            await session.execute(stmt)
            await session.commit()

    # ---- 읽기 작업 ----

    async def get_by_id(self, key: DomainKey) -> Domain:
        """기본 키로 도메인 객체를 조회한다.

        Args:
            key: 조회할 레코드의 기본 키.

        Returns:
            조회된 도메인 객체.

        Raises:
            NotFoundException: 해당 레코드가 없을 때.
        """
        async with self.session_factory() as session:  # type: ignore
            try:
                entity = await self._get_by_id(session, key)
                if entity is None:
                    raise NotFoundException(f"{self.entity} with key {key} not found.")
            except NoResultFound:
                raise NotFoundException(f"{self.entity} with key {key} not found.")
            except OperationalError as e:
                logger.error(f"Connection error while fetching entity {key}: {e}")
                raise
            except DataError as e:
                logger.error(f"Data error while fetching entity {key}: {e}")
                raise
            return entity.to_domain()

    async def find_by_id(self, key: DomainKey) -> Domain | None:
        """기본 키로 도메인 객체를 조회한다. 없으면 None을 반환한다.

        Args:
            key: 조회할 레코드의 기본 키.

        Returns:
            도메인 객체 또는 None.
        """
        async with self.session_factory() as session:  # type: ignore
            if entity := await self._find_by_id(session, key):
                return entity.to_domain()

    async def find_all(self) -> list[Domain]:
        """전체 레코드를 도메인 객체 리스트로 반환한다."""
        async with self.session_factory() as session:  # type: ignore
            stmt = self._get_select_based_on_relationship()
            result = await session.execute(stmt)
            entities = self._handle_scalars(result)
            return [entity.to_domain() for entity in entities]

    async def exist_by(self, **kwargs) -> bool:
        """조건에 맞는 레코드가 존재하는지 확인한다.

        Args:
            **kwargs: 필터 조건 (필드명=값).

        Returns:
            레코드가 존재하면 True.
        """
        async with self.session_factory() as session:  # type: ignore
            criteria = create_field_criteria(self.entity, kwargs)
            stmt = select(exists(self.entity)).where(*criteria)  # type: ignore
            result = await session.execute(stmt)
            return bool(result.scalar())

    async def count_by(self, **kwargs) -> int:
        """조건에 맞는 레코드 수를 반환한다.

        Args:
            **kwargs: 필터 조건 (필드명=값).

        Returns:
            매칭된 레코드 수.
        """
        async with self.session_factory() as session:  # type: ignore
            criteria = create_field_criteria(self.entity, kwargs)
            stmt = select(func.count()).select_from(self.entity).where(*criteria)  # type: ignore
            result = await session.execute(stmt)
            return result.scalar_one()

    async def get_by(self, **kwargs) -> Domain:
        """조건에 맞는 첫 번째 도메인 객체를 반환한다.

        Args:
            **kwargs: 필터 조건 (필드명=값).

        Returns:
            첫 번째 매칭 도메인 객체.

        Raises:
            NotFoundException: 매칭 결과가 없을 때.
        """
        domains = await self.find_by(**kwargs)
        if len(domains) == 0:
            raise NotFoundException(f"{self.entity} not found for {kwargs}.")
        return domains[0]

    async def find_by(self, **kwargs) -> list[Domain]:
        """조건에 맞는 모든 도메인 객체를 반환한다.

        Args:
            **kwargs: 필터 조건 (필드명=값).

        Returns:
            매칭된 도메인 객체 리스트.
        """
        async with self.session_factory() as session:  # type: ignore
            criteria = create_field_criteria(self.entity, kwargs)
            stmt = self._get_select_based_on_relationship().filter(*criteria)
            result = await session.execute(stmt)
            entities = self._handle_scalars(result)
            return [entity.to_domain() for entity in entities]

    # ---- 내부 헬퍼 ----

    def _get_select_based_on_relationship(self):
        if self._has_relationships():
            return self._get_joined_select()
        else:
            return select(self.entity)  # type: ignore

    def _get_joined_select(self):
        query = select(self.entity)  # type: ignore
        for attr in inspect(self.entity).relationships:  # type: ignore
            query = query.options(joinedload(attr.class_attribute))
        return query

    def _has_relationships(self):
        return bool(inspect(self.entity).relationships)  # type: ignore

    async def _get_by_id(self, session, key: DomainKey):
        criteria = create_id_criteria(self.entity, key)
        stmt = self._get_select_based_on_relationship().filter(*criteria)
        return self._handle_unique(await session.execute(stmt))

    async def _find_by_id(self, session, key: DomainKey):
        criteria = create_id_criteria(self.entity, key)
        stmt = self._get_select_based_on_relationship().filter(*criteria)
        return (await session.execute(stmt)).unique().scalars().one_or_none()

    async def _create(self, session, domain: Domain) -> None:
        entity = self.entity.from_domain(domain)
        session.add(entity)
        try:
            await session.flush()
        except IntegrityError as e:
            if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                raise AlreadyExistsException(f"{domain} already exists")
            else:
                logger.error(f"Integrity constraint violation: {e}")
                raise
        except DataError as e:
            logger.error(f"Data format error: {e}")
            raise
        except OperationalError as e:
            logger.error(f"Database connection/transaction error: {e}")
            raise

        if len(inspect(self.entity).relationships) > 0:  # type: ignore
            await session.refresh(entity)

        new_domain = entity.to_domain()
        reflect_domain(domain, new_domain)

    async def _update(self, session, entity, domain: Domain) -> None:
        entity.update(domain)
        await session.flush()

    def _handle_scalars(self, result):
        scalars = result.scalars()
        if self._has_relationships():
            return self._remove_duplicates(scalars)
        else:
            return scalars.all()

    def _handle_unique(self, result):
        if self._has_relationships():
            return result.unique().scalars().first()
        else:
            return result.scalars().one()

    def _remove_duplicates(self, scalars):
        return scalars.unique().all()


# ---- 모듈 레벨 헬퍼 함수 ----


def create_id_criteria(entity: Base, key: DomainKey):
    """기본 키(단일 또는 복합)로 SQLAlchemy 필터 조건을 생성한다.

    Args:
        entity: ORM 엔티티 클래스.
        key: 기본 키 값 (복합 키인 경우 튜플).

    Returns:
        SQLAlchemy BinaryExpression 리스트.
    """
    primary_keys = inspect(entity).primary_key  # type: ignore
    if len(primary_keys) == 1:
        return [primary_keys[0] == key]
    else:
        return [primary_key == k for primary_key, k in zip(primary_keys, key)]  # type: ignore


def create_field_criteria(entity, kwargs):
    """키워드 인자로 SQLAlchemy 필터 조건을 생성한다.

    Args:
        entity: ORM 엔티티 클래스.
        kwargs: 필드명=값 딕셔너리.

    Returns:
        SQLAlchemy BinaryExpression 리스트.
    """
    return [getattr(entity, key) == value for key, value in kwargs.items()]


def get_primary_key(entity: Base, domain: Domain):
    """도메인 객체에서 기본 키 값을 추출한다.

    엔티티의 ``from_domain`` → ``primary_key`` 체인을 통해 키를 얻습니다.

    Args:
        entity: ORM 엔티티 클래스.
        domain: 도메인 객체.

    Returns:
        기본 키 값.
    """
    return entity.from_domain(domain).primary_key()
