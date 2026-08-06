import {
  ChevronLeft,
  ChevronRight,
  Code2,
  Download,
  Loader2,
  ScanText,
  Share2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { clearCachedDetection, getDocument, readCachedDetection } from "@/api/client";
import { AppSidebar } from "@/components/AppSidebar";
import { DocumentCanvas } from "@/components/parser/DocumentCanvas";
import { MarkdownPanel } from "@/components/parser/MarkdownPanel";
import type { DetectionBlock, DetectionResult, DocumentPage } from "@/types/document";

function withUpdatedBlocks(
  result: DetectionResult,
  blocks: DetectionBlock[],
): DocumentPage[] {
  const byPage = new Map<number, DetectionBlock[]>();
  for (const block of blocks) {
    const list = byPage.get(block.page) ?? [];
    list.push(block);
    byPage.set(block.page, list);
  }
  return result.pages.map((page) => ({
    ...page,
    blocks: byPage.get(page.pageNumber) ?? page.blocks,
  }));
}

export function DocumentViewerPage() {
  const { documentId = "" } = useParams();
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [blocks, setBlocks] = useState<DetectionBlock[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [viewMode, setViewMode] = useState<"markdown" | "json">("markdown");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        // 서버 결과를 우선 조회 (재시작 후에도 디스크에서 복원). 캐시는 보조.
        let data = null as Awaited<ReturnType<typeof getDocument>> | null;
        try {
          data = await getDocument(documentId);
        } catch {
          data = readCachedDetection(documentId);
        }
        if (!data) {
          clearCachedDetection();
          throw new Error("Document not found. 서버가 꺼져 있거나 결과가 만료되었습니다. 홈에서 다시 Parse 하세요.");
        }
        if (cancelled) return;
        setResult(data);
        setBlocks(data.blocks);
        setSelectedId(data.blocks[0]?.id ?? null);
        setCurrentPage(data.pages[0]?.pageNumber ?? 1);
      } catch (e) {
        if (!cancelled) {
          clearCachedDetection();
          setError(e instanceof Error ? e.message : "Failed to load document");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  const pages = useMemo(
    () => (result ? withUpdatedBlocks(result, blocks) : []),
    [result, blocks],
  );

  const pageCount = result?.pageCount ?? pages.length;

  const handleBlockChange = (blockId: string, markdown: string) => {
    setBlocks((prev) =>
      prev.map((b) => (b.id === blockId ? { ...b, markdown } : b)),
    );
  };

  const goPage = (delta: number) => {
    if (!pageCount) return;
    const next = Math.min(pageCount, Math.max(1, currentPage + delta));
    setCurrentPage(next);
    setSelectedId(
      blocks.find((b) => b.page === next)?.id ?? selectedId,
    );
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center gap-2 text-zinc-500">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading detection…
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3">
        <p className="text-sm text-rose-600">{error ?? "Document not found"}</p>
        <Link to="/" className="text-sm text-zinc-700 underline">
          Back to home
        </Link>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-100">
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-zinc-200 bg-white px-4 py-2.5">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <Link to="/" className="truncate text-sm font-medium text-zinc-800 hover:underline">
              {result.filename}
            </Link>
            <button
              type="button"
              className="rounded p-1 text-zinc-400 hover:bg-zinc-100"
              aria-label="Download"
            >
              <Download className="h-4 w-4" />
            </button>
            <div className="ml-2 flex items-center gap-1 text-xs text-zinc-500">
              <button
                type="button"
                className="rounded p-0.5 hover:bg-zinc-100 disabled:opacity-40"
                disabled={currentPage <= 1}
                onClick={() => goPage(-1)}
                aria-label="Previous page"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <span>
                {currentPage} / {pageCount}
              </span>
              <button
                type="button"
                className="rounded p-0.5 hover:bg-zinc-100 disabled:opacity-40"
                disabled={currentPage >= pageCount}
                onClick={() => goPage(1)}
                aria-label="Next page"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-800"
            >
              <ScanText className="h-3.5 w-3.5" />
              Parse
            </button>
            <button
              type="button"
              className="rounded-full bg-sky-100 px-3 py-1.5 text-xs font-semibold text-sky-800"
            >
              Extract
            </button>
            <button
              type="button"
              className="rounded-full bg-zinc-100 px-3 py-1.5 text-xs font-semibold text-zinc-700"
            >
              + Tool
            </button>
          </div>

          <div className="flex flex-1 items-center justify-end gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2.5 py-1.5 text-xs text-zinc-600"
            >
              <Code2 className="h-3.5 w-3.5" />
              Get Code
            </button>
            <button
              type="button"
              className="rounded-lg border border-zinc-200 p-1.5 text-zinc-500"
              aria-label="Share"
            >
              <Share2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
          <div className="relative flex min-h-0 flex-col">
            <DocumentCanvas
              pages={pages}
              filename={result.filename}
              selectedId={selectedId}
              currentPage={currentPage}
              onSelect={setSelectedId}
              onPageChange={setCurrentPage}
            />
          </div>

          <MarkdownPanel
            blocks={blocks}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onBlockChange={handleBlockChange}
          />
        </div>
      </div>
    </div>
  );
}
