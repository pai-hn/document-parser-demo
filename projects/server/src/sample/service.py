"""Sample 애플리케이션 서비스 — 도메인 로직 오케스트레이션과 영속화.

새 도메인의 서비스를 만들 때 이 파일을 참고하세요.
서비스는 도메인 객체의 상태 변경 메서드를 호출한 뒤 레포지토리를 통해 저장하는
패턴을 따릅니다.
"""

from uuid import UUID

from src.sample.domains import Sample
from src.sample.repository import SampleRepository
from src.utils import new_uuid, utc_now


class SampleService:
    """Sample 도메인의 CRUD 및 상태 전이를 담당하는 서비스."""

    def __init__(self, sample_repo: SampleRepository):
        self._sample_repo = sample_repo

    async def create_sample(
        self,
        title: str,
        content: str,
        created_by: UUID,
    ) -> Sample:
        """새 샘플을 draft 상태로 생성한다.

        Args:
            title: 제목.
            content: 본문 내용.
            created_by: 작성자 사용자 ID.

        Returns:
            생성된 Sample 도메인 객체.
        """
        now = utc_now()
        sample = Sample(
            sample_id=new_uuid(),
            title=title,
            content=content,
            status="draft",
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        await self._sample_repo.create(sample)
        return sample

    async def get_sample(self, sample_id: UUID) -> Sample:
        """샘플을 기본 키로 조회한다.

        Args:
            sample_id: 조회할 샘플 ID.

        Returns:
            조회된 Sample 도메인 객체.

        Raises:
            NotFoundException: 샘플이 존재하지 않을 때.
        """
        return await self._sample_repo.get_by_id(sample_id)

    async def find_all(self) -> list[Sample]:
        """전체 샘플을 반환한다."""
        return await self._sample_repo.find_all()

    async def find_by_status(self, status: str) -> list[Sample]:
        """특정 상태의 샘플을 모두 반환한다.

        Args:
            status: 필터링할 상태 문자열.
        """
        return await self._sample_repo.find_by_status(status)

    async def publish(self, sample_id: UUID) -> Sample:
        """샘플을 draft → published로 전이한다.

        Args:
            sample_id: 대상 샘플 ID.

        Returns:
            전이된 Sample 도메인 객체.

        Raises:
            ValueError: 현재 상태가 draft가 아닐 때.
        """
        sample = await self._sample_repo.get_by_id(sample_id)
        sample.publish(updated_at=utc_now())
        await self._sample_repo.update(sample)
        return sample

    async def archive(self, sample_id: UUID) -> Sample:
        """샘플을 아카이브 처리한다.

        Args:
            sample_id: 대상 샘플 ID.

        Returns:
            아카이브된 Sample 도메인 객체.
        """
        sample = await self._sample_repo.get_by_id(sample_id)
        sample.archive(updated_at=utc_now())
        await self._sample_repo.update(sample)
        return sample

    async def update_content(self, sample_id: UUID, title: str, content: str) -> Sample:
        """draft 상태 샘플의 제목과 내용을 수정한다.

        Args:
            sample_id: 대상 샘플 ID.
            title: 새 제목.
            content: 새 내용.

        Returns:
            수정된 Sample 도메인 객체.

        Raises:
            ValueError: 샘플이 편집 가능한 상태(draft)가 아닐 때.
        """
        sample = await self._sample_repo.get_by_id(sample_id)
        sample.update_content(title=title, content=content, updated_at=utc_now())
        await self._sample_repo.update(sample)
        return sample
