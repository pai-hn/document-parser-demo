import type { BlockType } from "@/types/document";

/** Landing AI 스타일 참고 색상 (첨부 스크린샷 기준) */
export const BBOX_COLORS: Record<BlockType, string> = {
  text: "#22C55E",
  figure: "#EC4899",
  logo: "#EC4899",
  table: "#3B82F6",
  marginalia: "#A855F7",
};

/** 라벨 뱃지 글자색 — logo/marginalia는 검정, 나머지 흰색 */
export const BBOX_LABEL_TEXT: Record<BlockType, string> = {
  text: "#FFFFFF",
  figure: "#111827",
  logo: "#111827",
  table: "#FFFFFF",
  marginalia: "#111827",
};

export function blockLabel(index: number, type: BlockType): string {
  return `${index}.${type}`;
}
