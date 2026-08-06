import type { DetectionResult, SampleProject } from "@/types/document";
import { MOCK_DETECTION } from "@/lib/mockDetection";

const API_BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text();
    let message = text || `Request failed: ${res.status}`;
    try {
      const body = JSON.parse(text) as { message?: string };
      if (body.message) message = body.message;
    } catch {
      // keep raw text
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

function withApiPrefix(url: string): string {
  if (url.startsWith("/samples/") || url.startsWith("http") || url.startsWith("blob:")) {
    return url;
  }
  if (url.startsWith("/api/")) return url;
  if (url.startsWith("/")) return `/api${url}`;
  return url;
}

export async function listSamples(): Promise<SampleProject[]> {
  try {
    const samples = await request<SampleProject[]>("/documents/samples");
    return samples.map((s) => ({
      ...s,
      thumbnailUrl: withApiPrefix(s.thumbnailUrl),
    }));
  } catch {
    return [
      {
        sampleId: "fiscal-page",
        title: "3. 2026년 지방세 안내책 - 재정운영",
        fileCount: 1,
        thumbnailUrl: "/samples/fiscal-page.png",
      },
      {
        sampleId: "tax-guide",
        title: "3. 2026년 지방세 안내책",
        fileCount: 1,
        thumbnailUrl: "/samples/tax-guide.png",
      },
    ];
  }
}

function normalizeDetection(result: DetectionResult): DetectionResult {
  const pages = (result.pages ?? []).map((page) => ({
    ...page,
    imageUrl: withApiPrefix(page.imageUrl),
    blocks: page.blocks.map((b) => ({
      ...b,
      page: b.page ?? page.pageNumber,
    })),
  }));
  const blocks =
    result.blocks?.length > 0
      ? result.blocks.map((b) => ({ ...b, page: b.page ?? 1 }))
      : pages.flatMap((p) => p.blocks);

  return {
    ...result,
    pageCount: result.pageCount ?? pages.length,
    imageUrl: withApiPrefix(result.imageUrl),
    pages,
    blocks,
  };
}

export async function detectUpload(file: File): Promise<DetectionResult> {
  const form = new FormData();
  form.append("file", file);
  try {
    const result = await request<DetectionResult>("/documents/detect", {
      method: "POST",
      body: form,
    });
    return normalizeDetection(result);
  } catch {
    const objectUrl = URL.createObjectURL(file);
    return {
      ...MOCK_DETECTION,
      documentId: `local-${crypto.randomUUID()}`,
      filename: file.name,
      imageUrl: objectUrl,
      pages: [
        {
          ...MOCK_DETECTION.pages[0],
          imageUrl: objectUrl,
        },
      ],
    };
  }
}

export async function detectSample(sampleId: string): Promise<DetectionResult> {
  try {
    const result = await request<DetectionResult>(
      `/documents/samples/${sampleId}/detect`,
      { method: "POST" },
    );
    return normalizeDetection(result);
  } catch {
    const imageUrl =
      sampleId === "tax-guide" ? "/samples/tax-guide.png" : "/samples/fiscal-page.png";
    return {
      ...MOCK_DETECTION,
      documentId: `sample-${sampleId}`,
      filename:
        sampleId === "tax-guide"
          ? "2026년 지방세 안내책.png"
          : MOCK_DETECTION.filename,
      imageUrl,
      pages: [{ ...MOCK_DETECTION.pages[0], imageUrl }],
    };
  }
}

export async function getDocument(documentId: string): Promise<DetectionResult> {
  try {
    const result = await request<DetectionResult>(`/documents/${documentId}`);
    return normalizeDetection(result);
  } catch {
    if (
      documentId.startsWith("mock") ||
      documentId.startsWith("sample") ||
      documentId.startsWith("local")
    ) {
      return { ...MOCK_DETECTION, documentId };
    }
    throw new Error("Document not found");
  }
}

const STORAGE_KEY = "document-parser:last-result";

export function cacheDetectionResult(result: DetectionResult): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(result));
}

export function readCachedDetection(documentId: string): DetectionResult | null {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as DetectionResult;
    if (parsed.documentId === documentId) return normalizeDetection(parsed);
  } catch {
    return null;
  }
  return null;
}
