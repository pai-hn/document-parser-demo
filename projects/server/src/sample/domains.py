"""Sample 도메인 — 새 도메인을 추가할 때 참고할 수 있는 완전한 DDD 예제.

이 모듈은 표준 도메인 모델 패턴을 보여줍니다:

- ``@dataclass``로 도메인 객체를 정의
- 상태 전이는 반드시 메서드를 통해서만 수행 (외부에서 필드 직접 할당 금지)
- 타임스탬프는 메서드 파라미터로 주입
- 가드 절(guard clause)을 통해 유효한 상태 전이만 허용

상태 머신::

    draft → published → archived
    draft → archived
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Sample:
    """Sample 도메인 모델.

    Attributes:
        sample_id: 고유 식별자.
        title: 제목.
        content: 본문 내용.
        status: 현재 상태 ("draft" | "published" | "archived").
        created_by: 작성자 사용자 ID.
    """

    sample_id: UUID
    title: str
    content: str
    status: str  # "draft" | "published" | "archived"
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    # -- 조회 --

    def is_editable(self) -> bool:
        """draft 상태인 경우에만 편집이 가능하다."""
        return self.status == "draft"

    # -- 상태 변경 --

    def publish(self, *, updated_at: datetime) -> None:
        """draft → published로 상태를 전이한다.

        Args:
            updated_at: 변경 시각.

        Raises:
            ValueError: 현재 상태가 draft가 아닐 때.
        """
        if self.status != "draft":
            raise ValueError(f"Cannot publish from status '{self.status}'")
        self.status = "published"
        self.updated_at = updated_at

    def archive(self, *, updated_at: datetime) -> None:
        """어떤 상태에서든 archived로 전이한다.

        Args:
            updated_at: 변경 시각.
        """
        self.status = "archived"
        self.updated_at = updated_at

    def update_content(self, *, title: str, content: str, updated_at: datetime) -> None:
        """제목과 내용을 수정한다.

        Args:
            title: 새 제목.
            content: 새 내용.
            updated_at: 변경 시각.

        Raises:
            ValueError: 편집 가능한 상태(draft)가 아닐 때.
        """
        if not self.is_editable():
            raise ValueError(f"Cannot edit sample in status '{self.status}'")
        self.title = title
        self.content = content
        self.updated_at = updated_at
