import type { DetectionResult } from "@/types/document";

const page1Blocks = [
  {
    id: "1",
    index: 1,
    page: 1,
    type: "text" as const,
    bbox: { x: 0.08, y: 0.05, w: 0.72, h: 0.045 },
    markdown: "# 1. 기본현황 및 2026 재정운영 규모",
  },
  {
    id: "2",
    index: 2,
    page: 1,
    type: "text" as const,
    bbox: { x: 0.08, y: 0.12, w: 0.84, h: 0.14 },
    markdown:
      "- 일반현황: 인구 약 9만 명, 면적 약 455㎢, 행정구역 1읍 7면 2동\n- 재정규모: 일반회계·특별회계를 포함한 2026년 예산 총괄",
  },
  {
    id: "3",
    index: 3,
    page: 1,
    type: "figure" as const,
    bbox: { x: 0.1, y: 0.42, w: 0.8, h: 0.22 },
    markdown: "![세입·세출 도넛 차트](figure)",
  },
  {
    id: "4",
    index: 4,
    page: 1,
    type: "table" as const,
    bbox: { x: 0.08, y: 0.7, w: 0.84, h: 0.2 },
    markdown:
      "| 구분 | 공기업 특별회계 | 기타 특별회계 |\n| --- | --- | --- |\n| 세입 | 1,234 | 567 |\n| 세출 | 1,200 | 540 |",
  },
  {
    id: "5",
    index: 5,
    page: 1,
    type: "marginalia" as const,
    bbox: { x: 0.08, y: 0.93, w: 0.35, h: 0.03 },
    markdown: "1 _ 2026 지방세 안내",
  },
];

/** API 실패 시에만 사용하는 로컬 폴백 Detection 결과 */
export const MOCK_DETECTION: DetectionResult = {
  documentId: "mock-fiscal",
  filename: "2026년 지방세 안내책 - 재정운영.png",
  pageCount: 1,
  pageWidth: 900,
  pageHeight: 1200,
  imageUrl: "/samples/fiscal-page.png",
  pages: [
    {
      pageNumber: 1,
      width: 900,
      height: 1200,
      imageUrl: "/samples/fiscal-page.png",
      blocks: page1Blocks,
    },
  ],
  blocks: page1Blocks,
};
