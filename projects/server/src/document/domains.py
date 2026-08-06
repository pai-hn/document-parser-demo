"""Document Detection 도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

BlockType = Literal["text", "figure", "table", "marginalia"]


@dataclass(frozen=True)
class BBox:
    """정규화된 바운딩 박스 (0–1)."""

    x: float
    y: float
    w: float
    h: float


@dataclass
class DetectionBlock:
    """단일 Detection 블록."""

    id: str
    index: int
    page: int
    type: BlockType
    bbox: BBox
    markdown: str

    def update_markdown(self, *, markdown: str) -> None:
        """마크다운 내용을 수정한다."""
        self.markdown = markdown


@dataclass
class DocumentPage:
    """문서의 단일 페이지."""

    page_number: int
    width: int
    height: int
    image_path: str
    blocks: list[DetectionBlock] = field(default_factory=list)

    def image_url_for(self, document_id: UUID) -> str:
        """클라이언트가 페이지 이미지를 조회할 상대 경로."""
        return f"/documents/{document_id}/pages/{self.page_number}/image"


@dataclass
class DetectionResult:
    """문서 Detection 결과 (멀티 페이지)."""

    document_id: UUID
    filename: str
    pages: list[DocumentPage] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        """총 페이지 수."""
        return len(self.pages)

    @property
    def blocks(self) -> list[DetectionBlock]:
        """모든 페이지의 블록을 순서대로 합친 목록."""
        return [block for page in self.pages for block in page.blocks]

    @property
    def page_width(self) -> int:
        """첫 페이지 너비 (하위 호환)."""
        return self.pages[0].width if self.pages else 0

    @property
    def page_height(self) -> int:
        """첫 페이지 높이 (하위 호환)."""
        return self.pages[0].height if self.pages else 0

    @property
    def image_url(self) -> str:
        """첫 페이지 이미지 URL (하위 호환)."""
        if not self.pages:
            return f"/documents/{self.document_id}/pages/1/image"
        return self.pages[0].image_url_for(self.document_id)

    def get_page(self, page_number: int) -> DocumentPage:
        """1-based 페이지를 조회한다."""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        raise KeyError(page_number)


@dataclass(frozen=True)
class SampleProject:
    """데모용 샘플 프로젝트 메타데이터."""

    sample_id: str
    title: str
    file_count: int
    filename: str
