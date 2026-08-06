import { ChevronLeft, ChevronRight, Loader2, Minus, Pencil, Plus, Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getDocument, readCachedDetection } from "@/api/client";
import { ConsoleLayout, ConsolePageHeading, primaryButtonClass } from "@/components/ConsoleLayout";
import { DocumentCanvas } from "@/components/parser/DocumentCanvas";
import { BBOX_COLORS } from "@/lib/bboxColors";
import type { BlockType, DetectionResult } from "@/types/document";

const TYPE_LABELS: Record<BlockType, string> = {
  figure: "그림",
  text: "텍스트",
  table: "표",
  marginalia: "여백 요소",
};

export function DocumentResultPage() {
  const { documentId = "" } = useParams();
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(100);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = readCachedDetection(documentId) ?? (await getDocument(documentId));
        if (!cancelled) {
          setResult(data);
          setCurrentPage(data.pages[0]?.pageNumber ?? 1);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "문서를 불러오지 못했습니다.");
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [documentId]);

  const counts = useMemo(() => {
    const base: Record<BlockType, number> = { figure: 0, text: 0, table: 0, marginalia: 0 };
    for (const block of result?.blocks ?? []) base[block.type] += 1;
    return base;
  }, [result]);

  if (error) {
    return <ConsoleLayout><main className="flex flex-1 flex-col items-center justify-center gap-3"><p className="text-red-600">{error}</p><Link to="/" className="text-blue-700 underline">PDF 업로드로 돌아가기</Link></main></ConsoleLayout>;
  }
  if (!result) {
    return <ConsoleLayout><main className="flex flex-1 items-center justify-center gap-2 text-slate-600"><Loader2 className="h-5 w-5 animate-spin" /> 분석 결과 불러오는 중</main></ConsoleLayout>;
  }

  const total = result.blocks.length;
  const goPage = (delta: number) => setCurrentPage((value) => Math.min(result.pageCount, Math.max(1, value + delta)));

  return (
    <ConsoleLayout>
      <main className="flex h-[calc(100vh-5rem)] min-h-[650px] flex-col gap-3 overflow-hidden p-3">
        <ConsolePageHeading actions={<><Link to="/" className={primaryButtonClass}><Upload className="h-4 w-4" />PDF 업로드</Link><Link to={`/documents/${documentId}/edit`} className={primaryButtonClass}><Pencil className="h-4 w-4" />수정</Link></>} />
        <div className="grid min-h-0 flex-1 grid-cols-[230px_minmax(500px,1fr)_320px] gap-3">
          <aside className="overflow-auto rounded border border-slate-200 bg-white p-2 shadow-sm">
            <h2 className="border-b px-1 pb-2 text-base font-bold">문서</h2>
            <div className="mt-2 rounded border border-blue-500 bg-blue-50 p-2.5">
              <p className="break-all text-sm font-bold">1. {result.filename}</p>
              <p className="mt-1 text-xs text-slate-700">{result.pageCount}쪽 · detected</p>
            </div>
          </aside>

          <section className="flex min-h-0 flex-col overflow-hidden rounded border border-slate-200 bg-white shadow-sm">
            <div className="m-2 flex h-12 shrink-0 items-center justify-center gap-2 rounded border border-slate-400 bg-white text-sm">
              <button type="button" disabled={currentPage <= 1} onClick={() => goPage(-1)} className="console-tool"><ChevronLeft className="h-4 w-4" />이전</button>
              <input aria-label="현재 페이지" value={currentPage} onChange={(e) => setCurrentPage(Math.min(result.pageCount, Math.max(1, Number(e.target.value) || 1)))} className="h-8 w-14 rounded border border-slate-500 text-center" />
              <span>/ {result.pageCount}</span>
              <button type="button" disabled={currentPage >= result.pageCount} onClick={() => goPage(1)} className="console-tool">다음<ChevronRight className="h-4 w-4" /></button>
              <span className="mx-1 h-6 border-l" />
              <button type="button" onClick={() => setZoom((value) => Math.max(50, value - 10))} className="console-tool"><Minus className="h-4 w-4" />축소</button>
              <span className="w-11 text-center">{zoom}%</span>
              <button type="button" onClick={() => setZoom((value) => Math.min(180, value + 10))} className="console-tool"><Plus className="h-4 w-4" />확대</button>
            </div>
            <DocumentCanvas
              pages={result.pages}
              filename={result.filename}
              selectedId={selectedId}
              currentPage={currentPage}
              onSelect={setSelectedId}
              onPageChange={setCurrentPage}
              zoomPercent={zoom}
              showThumbnails={false}
            />
          </section>

          <aside className="min-h-0 overflow-auto rounded border border-slate-200 bg-white p-3 shadow-sm">
            <h2 className="border-b pb-2 text-base font-bold">분석 결과</h2>
            <div className="space-y-1 py-3 text-sm"><p>전체 요소 {total}개</p><p>전체 페이지 {result.pageCount}쪽</p></div>
            <div className="space-y-3">
              {(Object.keys(TYPE_LABELS) as BlockType[]).map((type) => {
                const percent = total ? Math.round((counts[type] / total) * 100) : 0;
                return <div key={type}><div className="flex justify-between text-sm"><span>{TYPE_LABELS[type]}</span><span>{counts[type]} · {percent}%</span></div><div className="mt-1 h-1.5 overflow-hidden rounded bg-slate-100"><div className="h-full rounded" style={{ width: `${percent}%`, backgroundColor: BBOX_COLORS[type] }} /></div></div>;
              })}
            </div>
            <h3 className="mt-5 border-t pt-4 text-sm font-bold">페이지별 요소 분포</h3>
            <div className="mt-3 grid grid-cols-3 gap-1.5">
              {result.pages.map((item) => <button key={item.pageNumber} type="button" onClick={() => setCurrentPage(item.pageNumber)} className={`min-h-14 rounded border p-1.5 text-left ${item.pageNumber === currentPage ? "border-blue-500 bg-blue-50" : "border-slate-400"}`}><strong className="text-xs">{item.pageNumber}쪽</strong><p className="mt-1 text-[11px] leading-tight text-slate-600">요소 {item.blocks.length}</p></button>)}
            </div>
          </aside>
        </div>
      </main>
    </ConsoleLayout>
  );
}
