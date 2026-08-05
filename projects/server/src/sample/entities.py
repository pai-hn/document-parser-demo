"""Sample 도메인의 SQLAlchemy ORM 엔티티.

``samples`` 테이블과 매핑되며, ``Base[UUID, Sample]``을 상속하여
도메인 ↔ 엔티티 간 양방향 변환 메서드를 제공합니다.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import TIMESTAMP, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.sample.domains import Sample
from src.storages.database.base import Base


class SampleEntity(Base[UUID, Sample]):
    __tablename__ = "samples"

    sample_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_by: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    @staticmethod
    def from_domain(domain: Sample) -> "SampleEntity":
        """Sample 도메인 객체로부터 엔티티를 생성한다."""
        return SampleEntity(
            sample_id=domain.sample_id,
            title=domain.title,
            content=domain.content,
            status=domain.status,
            created_by=domain.created_by,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    def to_domain(self) -> Sample:
        """엔티티를 Sample 도메인 객체로 변환한다."""
        return Sample(
            sample_id=self.sample_id,
            title=self.title,
            content=self.content,
            status=self.status,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def update(self, domain: Sample) -> None:
        """도메인 객체의 현재 상태를 엔티티에 반영한다."""
        self.title = domain.title
        self.content = domain.content
        self.status = domain.status
        self.updated_at = domain.updated_at

    def primary_key(self) -> UUID:
        return self.sample_id
