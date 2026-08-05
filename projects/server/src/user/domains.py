"""사용자 도메인 모델.

역할 기반 접근 제어와 상태 변경 메서드를 포함하는 User 데이터클래스를 정의합니다.
모든 필드 변경은 명시적 메서드를 통해서만 이루어지며,
비밀번호 변경 시 ``must_change_password`` 플래그가 자동 해제되는 등의
비즈니스 규칙이 한 곳에서 관리됩니다.

역할 체계::

    master (3)  — 시스템 전체 관리
    admin  (2)  — 팀 관리
    member (1)  — 일반 사용자
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

ROLE_LEVELS = {"master": 3, "admin": 2, "member": 1}
_PRIVILEGED_ROLES = ("master", "admin")


@dataclass
class User:
    """사용자 도메인 모델.

    Attributes:
        user_id: 고유 식별자.
        username: 로그인 아이디 (유니크).
        hashed_password: bcrypt 해시된 비밀번호.
        role: 역할 ("master" | "admin" | "member").
        team_id: 소속 팀 ID (없으면 None).
        is_active: 계정 활성 여부.
        must_change_password: 최초 로그인 시 비밀번호 변경 필요 여부.
    """

    user_id: UUID
    username: str
    hashed_password: str
    role: str  # "master" | "admin" | "member"
    team_id: UUID | None
    is_active: bool
    must_change_password: bool
    display_name: str | None = None
    github_username: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime = None  # type: ignore[assignment]
    updated_at: datetime = None  # type: ignore[assignment]

    # -- 조회 --

    def has_min_role(self, min_role: str) -> bool:
        """사용자의 역할이 ``min_role`` 이상인지 확인한다.

        Args:
            min_role: 최소 요구 역할 ("member", "admin", "master").

        Returns:
            역할 레벨이 충분하면 True.
        """
        return ROLE_LEVELS.get(self.role, 0) >= ROLE_LEVELS.get(min_role, 0)

    def is_privileged(self) -> bool:
        """admin 또는 master 권한을 가지고 있는지 확인한다."""
        return self.role in _PRIVILEGED_ROLES

    # -- 상태 변경 --

    def change_password(self, *, hashed_password: str, updated_at: datetime) -> None:
        """비밀번호를 변경하고 강제 변경 플래그를 해제한다.

        Args:
            hashed_password: 새로운 bcrypt 해시 비밀번호.
            updated_at: 변경 시각.
        """
        self.hashed_password = hashed_password
        self.must_change_password = False
        self.updated_at = updated_at

    def deactivate(self, *, updated_at: datetime) -> None:
        """계정을 비활성화한다."""
        self.is_active = False
        self.updated_at = updated_at

    def activate(self, *, updated_at: datetime) -> None:
        """계정을 활성화한다."""
        self.is_active = True
        self.updated_at = updated_at

    def change_role(self, *, role: str, updated_at: datetime) -> None:
        """역할을 변경한다.

        Args:
            role: 새로운 역할 ("master", "admin", "member").
            updated_at: 변경 시각.
        """
        self.role = role
        self.updated_at = updated_at

    def update_profile(
        self,
        *,
        display_name: str | None = None,
        github_username: str | None = None,
        updated_at: datetime,
    ) -> None:
        """선택적 프로필 필드를 갱신한다.

        None이 아닌 값만 실제로 반영됩니다.

        Args:
            display_name: 표시 이름 (None이면 변경 안 함).
            github_username: GitHub 사용자명 (None이면 변경 안 함).
            updated_at: 변경 시각.
        """
        if display_name is not None:
            self.display_name = display_name
        if github_username is not None:
            self.github_username = github_username
        self.updated_at = updated_at

    def assign_team(self, *, team_id: UUID | None, updated_at: datetime) -> None:
        """소속 팀을 변경한다.

        Args:
            team_id: 새 팀 ID (None이면 팀 해제).
            updated_at: 변경 시각.
        """
        self.team_id = team_id
        self.updated_at = updated_at
