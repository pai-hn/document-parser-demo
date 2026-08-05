"""User 레포지토리 — BaseRepository 위에 사용자 전용 쿼리를 추가합니다."""

from uuid import UUID

from sqlalchemy import select

from src.storages.database.repository import BaseRepository
from src.user.domains import User
from src.user.entities import UserEntity


class UserRepository(BaseRepository[UUID, User]):
    entity: type[UserEntity] = UserEntity

    async def find_by_username(self, username: str) -> User | None:
        """유니크한 username으로 사용자를 조회한다.

        Args:
            username: 조회할 사용자 아이디.

        Returns:
            매칭되는 User 또는 None.
        """
        async with self.session_factory() as session:
            stmt = select(UserEntity).where(UserEntity.username == username)
            result = await session.execute(stmt)
            entity = result.scalars().one_or_none()
            if entity is None:
                return None
            return entity.to_domain()

    async def find_by_team_id(self, team_id: UUID) -> list[User]:
        """특정 팀에 소속된 모든 사용자를 반환한다.

        Args:
            team_id: 팀 ID.

        Returns:
            해당 팀의 사용자 리스트.
        """
        async with self.session_factory() as session:
            stmt = select(UserEntity).where(UserEntity.team_id == team_id)
            result = await session.execute(stmt)
            return [e.to_domain() for e in result.scalars().all()]
