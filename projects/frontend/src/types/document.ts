export type BlockType = "text" | "figure" | "table" | "marginalia" | "logo";

export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface DetectionBlock {
  id: string;
  index: number;
  page: number;
  type: BlockType;
  bbox: BBox;
  markdown: string;
  html?: string;
  bboxXyxy?: number[];
}

export interface DocumentPage {
  pageNumber: number;
  width: number;
  height: number;
  imageUrl: string;
  blocks: DetectionBlock[];
}

export interface DetectionResult {
  documentId: string;
  filename: string;
  pageCount: number;
  pageWidth: number;
  pageHeight: number;
  imageUrl: string;
  pages: DocumentPage[];
  blocks: DetectionBlock[];
}

export interface SampleProject {
  sampleId: string;
  title: string;
  fileCount: number;
  thumbnailUrl: string;
}
