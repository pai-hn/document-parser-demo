"""사용자 애플리케이션 서비스 — CRUD 및 비밀번호 관리.

사용자 생성, 비밀번호 변경, 프로필 수정 등 사용자 도메인의 비즈니스 로직을
오케스트레이션합니다. 도메인 객체의 상태 변경 메서드를 호출한 뒤
레포지토리를 통해 영속화하는 패턴을 따릅니다.
"""

from uuid import UUID

from src.common.exceptions import BadRequestException
from src.user.domains import User
from src.user.password import hash_password, verify_password
from src.user.repository import UserRepository
from src.utils import new_uuid, utc_now


class UserService:
    """사용자 CRUD, 비밀번호 관리, 프로필 작업을 담당하는 서비스."""

    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def create_user(
        self,
        username: str,
        password: str,
        role: str = "member",
        team_id: UUID | None = None,
        display_name: str | None = None,
        github_username: str | None = None,
    ) -> User:
        """새 사용자를 생성한다.

        Args:
            username: 로그인 아이디.
            password: 평문 비밀번호 (내부적으로 해시 처리).
            role: 역할 (기본값 "member").
            team_id: 소속 팀 ID.
            display_name: 표시 이름.
            github_username: GitHub 사용자명.

        Returns:
            생성된 User 도메인 객체.

        Raises:
            AlreadyExistsException: 동일한 username이 이미 존재할 때.
        """
        now = utc_now()
        user = User(
            user_id=new_uuid(),
            username=username,
            hashed_password=hash_password(password),
            display_name=display_name,
            role=role,
            team_id=team_id,
            github_username=github_username,
            is_active=True,
            must_change_password=False,
            created_at=now,
            updated_at=now,
        )
        await self._user_repo.create(user)
        return user

    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        """현재 비밀번호를 검증한 뒤 새 비밀번호로 변경한다.

        Args:
            user_id: 대상 사용자 ID.
            current_password: 현재 비밀번호 (평문).
            new_password: 새 비밀번호 (평문).

        Raises:
            BadRequestException: 현재 비밀번호가 틀렸을 때.
            NotFoundException: 사용자가 존재하지 않을 때.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not verify_password(current_password, user.hashed_password):
            raise BadRequestException("Current password is incorrect")
        user.change_password(
            hashed_password=hash_password(new_password),
            updated_at=utc_now(),
        )
        await self._user_repo.update(user)

    async def get_user(self, user_id: UUID) -> User:
        """사용자를 기본 키로 조회한다.

        Args:
            user_id: 사용자 ID.

        Returns:
            조회된 User 도메인 객체.

        Raises:
            NotFoundException: 사용자가 존재하지 않을 때.
        """
        return await self._user_repo.get_by_id(user_id)

    async def find_all(self) -> list[User]:
        """전체 사용자를 반환한다."""
        return await self._user_repo.find_all()

    async def find_by_team_id(self, team_id: UUID) -> list[User]:
        """특정 팀에 소속된 사용자를 모두 반환한다.

        Args:
            team_id: 팀 ID.
        """
        return await self._user_repo.find_by_team_id(team_id)

    async def admin_reset_password(self, user_id: UUID, new_password: str) -> None:
        """관리자 전용: 기존 비밀번호 확인 없이 비밀번호를 재설정한다.

        Args:
            user_id: 대상 사용자 ID.
            new_password: 새 비밀번호 (평문).
        """
        user = await self._user_repo.get_by_id(user_id)
        user.change_password(
            hashed_password=hash_password(new_password),
            updated_at=utc_now(),
        )
        await self._user_repo.update(user)

    async def update_user(self, user: User) -> None:
        """이미 변경된 User 도메인 객체를 DB에 반영한다.

        도메인 메서드(deactivate, change_role 등)를 호출한 뒤 이 메서드로 영속화합니다.

        Args:
            user: 변경이 완료된 User 객체.
        """
        await self._user_repo.update(user)
