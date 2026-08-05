"""SQLAlchemy 선언적 베이스 및 도메인 매핑 인터페이스.

모든 ORM 엔티티는 ``Base[DomainKey, Domain]``을 상속하며,
네 가지 추상 메서드(``from_domain``, ``to_domain``, ``update``, ``primary_key``)를
구현해야 합니다. 이를 통해 영속 계층과 도메인 계층을 분리하면서도
제네릭 레포지토리에서 모든 엔티티를 동일한 인터페이스로 다룰 수 있습니다.

Usage::

    class UserEntity(Base[UUID, User]):
        __tablename__ = "users"
        # ... 컬럼 정의 ...

        @staticmethod
        def from_domain(domain: User) -> "UserEntity":
            return UserEntity(user_id=domain.user_id, ...)

        def to_domain(self) -> User:
            return User(user_id=self.user_id, ...)

        def update(self, domain: User) -> None:
            self.username = domain.username
            ...

        def primary_key(self) -> UUID:
            return self.user_id
"""

from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

DomainKey = TypeVar("DomainKey")
Domain = TypeVar("Domain")


class Base(AsyncAttrs, DeclarativeBase, Generic[DomainKey, Domain]):
    """모든 ORM 엔티티의 기반 클래스.

    제네릭 타입 파라미터:
        DomainKey: 기본 키 타입 (예: ``UUID``, ``tuple[UUID, UUID]``).
        Domain: 대응하는 도메인 모델 타입 (예: ``User``).
    """

    __abstract__ = True

    @staticmethod
    def from_domain(domain: Domain):
        """도메인 객체로부터 엔티티 인스턴스를 생성한다."""
        raise NotImplementedError("from_domain method is not implemented")

    def to_domain(self) -> Domain:
        """엔티티를 도메인 객체로 변환한다."""
        raise NotImplementedError("to_domain method is not implemented")

    def update(self, domain: Domain):
        """도메인 객체의 변경 사항을 엔티티에 반영한다."""
        raise NotImplementedError("update method is not implemented")

    def primary_key(self) -> DomainKey:
        """엔티티의 기본 키 값을 반환한다."""
        raise NotImplementedError("primary_key method is not implemented")
