import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getDocument, readCachedDetection } from "@/api/client";
import { ConsoleLayout, ConsolePageHeading, primaryButtonClass } from "@/components/ConsoleLayout";
import { DocumentCanvas } from "@/components/parser/DocumentCanvas";
import { MarkdownPanel } from "@/components/parser/MarkdownPanel";
import type { DetectionBlock, DetectionResult, DocumentPage } from "@/types/document";

function withUpdatedBlocks(result: DetectionResult, blocks: DetectionBlock[]): DocumentPage[] {
  const byPage = new Map<number, DetectionBlock[]>();
  for (const block of blocks) byPage.set(block.page, [...(byPage.get(block.page) ?? []), block]);
  return result.pages.map((page) => ({ ...page, blocks: byPage.get(page.pageNumber) ?? page.blocks }));
}

export function DocumentViewerPage() {
  const { documentId = "" } = useParams();
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [blocks, setBlocks] = useState<DetectionBlock[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [viewMode, setViewMode] = useState<"markdown" | "json">("markdown");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = readCachedDetection(documentId) ?? (await getDocument(documentId));
        if (!cancelled) {
          setResult(data);
          setBlocks(data.blocks);
          setSelectedId(data.blocks[0]?.id ?? null);
          setCurrentPage(data.pages[0]?.pageNumber ?? 1);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "문서를 불러오지 못했습니다.");
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [documentId]);

  const pages = useMemo(() => result ? withUpdatedBlocks(result, blocks) : [], [result, blocks]);
  const goPage = (delta: number) => {
    if (!result) return;
    const next = Math.min(result.pageCount, Math.max(1, currentPage + delta));
    setCurrentPage(next);
    setSelectedId(blocks.find((block) => block.page === next)?.id ?? selectedId);
  };

  if (error) return <ConsoleLayout><main className="flex flex-1 flex-col items-center justify-center gap-3"><p className="text-red-600">{error}</p><Link to="/" className="text-blue-700 underline">PDF 업로드로 돌아가기</Link></main></ConsoleLayout>;
  if (!result) return <ConsoleLayout><main className="flex flex-1 items-center justify-center gap-2 text-slate-600"><Loader2 className="h-5 w-5 animate-spin" /> 편집 화면 불러오는 중</main></ConsoleLayout>;

  return (
    <ConsoleLayout>
      <main className="flex h-[calc(100vh-5rem)] min-h-[650px] flex-col gap-3 overflow-hidden p-3">
        <ConsolePageHeading actions={<Link to={`/documents/${documentId}`} className={primaryButtonClass}>분석 결과로 돌아가기</Link>} />
        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded border border-slate-200 bg-white shadow-sm">
          <div className="flex h-11 shrink-0 items-center border-b px-4">
            <strong className="min-w-0 flex-1 truncate text-sm">{result.filename}</strong>
            <div className="flex items-center gap-2 text-sm">
              <button type="button" disabled={currentPage <= 1} onClick={() => goPage(-1)} className="console-tool"><ChevronLeft className="h-4 w-4" /></button>
              <span>{currentPage} / {result.pageCount}</span>
              <button type="button" disabled={currentPage >= result.pageCount} onClick={() => goPage(1)} className="console-tool"><ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
          <div className="grid min-h-0 flex-1 grid-cols-2">
            <DocumentCanvas pages={pages} filename={result.filename} selectedId={selectedId} currentPage={currentPage} onSelect={setSelectedId} onPageChange={setCurrentPage} />
            <MarkdownPanel blocks={blocks} viewMode={viewMode} onViewModeChange={setViewMode} selectedId={selectedId} onSelect={setSelectedId} onBlockChange={(blockId, markdown) => setBlocks((current) => current.map((block) => block.id === blockId ? { ...block, markdown } : block))} />
          </div>
        </section>
      </main>
    </ConsoleLayout>
  );
}
