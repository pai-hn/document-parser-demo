"""Sample 레포지토리 — BaseRepository 위에 도메인별 커스텀 쿼리를 추가합니다.

새 도메인의 레포지토리를 만들 때 이 파일을 참고하세요.
``entity`` 클래스 변수만 지정하면 CRUD는 자동 제공되므로,
커스텀 쿼리만 추가하면 됩니다.
"""

from uuid import UUID

from sqlalchemy import select

from src.sample.domains import Sample
from src.sample.entities import SampleEntity
from src.storages.database.repository import BaseRepository


class SampleRepository(BaseRepository[UUID, Sample]):
    entity: type[SampleEntity] = SampleEntity

    async def find_by_status(self, status: str) -> list[Sample]:
        """특정 상태의 샘플을 모두 반환한다.

        Args:
            status: 필터링할 상태 ("draft", "published", "archived").

        Returns:
            매칭된 Sample 리스트.
        """
        async with self.session_factory() as session:
            stmt = select(SampleEntity).where(SampleEntity.status == status)
            result = await session.execute(stmt)
            return [e.to_domain() for e in result.scalars().all()]

    async def find_by_created_by(self, user_id: UUID) -> list[Sample]:
        """특정 사용자가 작성한 샘플을 모두 반환한다.

        Args:
            user_id: 작성자 사용자 ID.

        Returns:
            매칭된 Sample 리스트.
        """
        async with self.session_factory() as session:
            stmt = select(SampleEntity).where(SampleEntity.created_by == user_id)
            result = await session.execute(stmt)
            return [e.to_domain() for e in result.scalars().all()]
