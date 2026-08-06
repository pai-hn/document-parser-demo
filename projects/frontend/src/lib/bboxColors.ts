import type { BlockType } from "@/types/document";

export const BBOX_COLORS: Record<BlockType, string> = {
  text: "#22C55E",
  figure: "#EC4899",
  table: "#3B82F6",
  marginalia: "#A855F7",
};

export function blockLabel(index: number, type: BlockType): string {
  return `${index}.${type}`;
}
