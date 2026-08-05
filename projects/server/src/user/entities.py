"""User 도메인의 SQLAlchemy ORM 엔티티.

``users`` 테이블과 매핑되며, ``Base[UUID, User]``를 상속하여
도메인 ↔ 엔티티 간 양방향 변환 메서드를 제공합니다.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import TIMESTAMP, Boolean, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.storages.database.base import Base
from src.user.domains import User


class UserEntity(Base[UUID, User]):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    team_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, default=None)
    github_username: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    @staticmethod
    def from_domain(domain: User) -> "UserEntity":
        """User 도메인 객체로부터 엔티티를 생성한다."""
        return UserEntity(
            user_id=domain.user_id,
            username=domain.username,
            hashed_password=domain.hashed_password,
            display_name=domain.display_name,
            role=domain.role,
            team_id=domain.team_id,
            github_username=domain.github_username,
            is_active=domain.is_active,
            must_change_password=domain.must_change_password,
            last_login_at=domain.last_login_at,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    def to_domain(self) -> User:
        """엔티티를 User 도메인 객체로 변환한다."""
        return User(
            user_id=self.user_id,
            username=self.username,
            hashed_password=self.hashed_password,
            display_name=self.display_name,
            role=self.role,
            team_id=self.team_id,
            github_username=self.github_username,
            is_active=self.is_active,
            must_change_password=self.must_change_password,
            last_login_at=self.last_login_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def update(self, domain: User) -> None:
        """도메인 객체의 현재 상태를 엔티티에 반영한다."""
        self.username = domain.username
        self.hashed_password = domain.hashed_password
        self.display_name = domain.display_name
        self.role = domain.role
        self.team_id = domain.team_id
        self.github_username = domain.github_username
        self.is_active = domain.is_active
        self.must_change_password = domain.must_change_password
        self.last_login_at = domain.last_login_at
        self.updated_at = domain.updated_at

    def primary_key(self) -> UUID:
        return self.user_id
