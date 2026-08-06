import { useEffect, useRef, useState } from "react";
import { BBOX_COLORS, blockLabel } from "@/lib/bboxColors";
import { resolveImageUrl } from "@/lib/imageUrl";
import type { DetectionBlock, DocumentPage } from "@/types/document";

interface DocumentCanvasProps {
  pages: DocumentPage[];
  filename: string;
  selectedId: string | null;
  currentPage: number;
  onSelect: (blockId: string) => void;
  onPageChange: (pageNumber: number) => void;
  zoomPercent?: number;
  showThumbnails?: boolean;
}

function PageView({
  page,
  filename,
  selectedId,
  onSelect,
  pageRef,
  zoomPercent,
}: {
  page: DocumentPage;
  filename: string;
  selectedId: string | null;
  onSelect: (blockId: string) => void;
  pageRef: (el: HTMLDivElement | null) => void;
  zoomPercent: number;
}) {
  const [failed, setFailed] = useState(false);
  const imageUrl = resolveImageUrl(page.imageUrl);

  useEffect(() => {
    setFailed(false);
  }, [imageUrl]);

  return (
    <div
      ref={pageRef}
      data-page={page.pageNumber}
      className="relative mx-auto overflow-hidden rounded-sm bg-white shadow-sm"
      style={{
        width: `${zoomPercent}%`,
        maxWidth: `${Math.round((page.width * zoomPercent) / 100)}px`,
        aspectRatio: `${page.width} / ${page.height}`,
      }}
    >
      <div className="absolute right-2 top-2 z-30 rounded bg-black/55 px-2 py-0.5 text-[11px] font-medium text-white">
        {page.pageNumber}
      </div>
      {failed ? (
        <div className="flex min-h-[420px] flex-col items-center justify-center gap-2 px-6 text-center text-sm text-zinc-500">
          <p>페이지 {page.pageNumber} 이미지를 불러오지 못했습니다.</p>
          <p className="text-xs text-zinc-400">{filename}</p>
        </div>
      ) : (
        <img
          key={imageUrl}
          src={imageUrl}
          alt={`${filename} — page ${page.pageNumber}`}
          className="block h-auto w-full select-none"
          draggable={false}
          onLoad={() => setFailed(false)}
          onError={() => {
            setFailed(true);
          }}
        />
      )}
      {!failed &&
        page.blocks.map((block: DetectionBlock) => {
          const color = BBOX_COLORS[block.type];
          const selected = selectedId === block.id;
          return (
            <button
              key={block.id}
              type="button"
              onClick={() => onSelect(block.id)}
              className="absolute box-border cursor-pointer border-2 transition"
              style={{
                left: `${block.bbox.x * 100}%`,
                top: `${block.bbox.y * 100}%`,
                width: `${block.bbox.w * 100}%`,
                height: `${block.bbox.h * 100}%`,
                borderColor: color,
                backgroundColor: selected ? `${color}33` : `${color}14`,
                outline: selected ? `2px solid ${color}` : undefined,
                outlineOffset: selected ? 1 : undefined,
                zIndex: selected ? 20 : 10,
              }}
              aria-label={blockLabel(block.index, block.type)}
            >
              <span
                className="absolute -top-5 left-0 rounded-sm px-1.5 py-0.5 text-[11px] font-semibold leading-none text-white"
                style={{ backgroundColor: color }}
              >
                {blockLabel(block.index, block.type)}
              </span>
            </button>
          );
        })}
    </div>
  );
}

export function DocumentCanvas({
  pages,
  filename,
  selectedId,
  currentPage,
  onSelect,
  onPageChange,
  zoomPercent = 100,
  showThumbnails = true,
}: DocumentCanvasProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const suppressObserver = useRef(false);

  useEffect(() => {
    const root = scrollRef.current;
    if (!root) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (suppressObserver.current) return;
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        const top = visible[0];
        if (!top) return;
        const page = Number((top.target as HTMLElement).dataset.page);
        if (page && page !== currentPage) onPageChange(page);
      },
      { root, threshold: [0.35, 0.55, 0.75] },
    );

    for (const page of pages) {
      const el = pageRefs.current[page.pageNumber];
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [pages, currentPage, onPageChange]);

  const scrollToPage = (pageNumber: number, align: ScrollLogicalPosition = "start") => {
    const el = pageRefs.current[pageNumber];
    if (!el) return;
    suppressObserver.current = true;
    el.scrollIntoView({ behavior: "smooth", block: align });
    onPageChange(pageNumber);
    window.setTimeout(() => {
      suppressObserver.current = false;
    }, 500);
  };

  useEffect(() => {
    if (!selectedId) return;
    const block = pages.flatMap((p) => p.blocks).find((b) => b.id === selectedId);
    if (!block) return;
    scrollToPage(block.page, "center");
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only react to selection changes
  }, [selectedId]);

  useEffect(() => {
    const el = pageRefs.current[currentPage];
    if (!el || !scrollRef.current) return;
    const root = scrollRef.current;
    const rect = el.getBoundingClientRect();
    const rootRect = root.getBoundingClientRect();
    const visible =
      rect.top < rootRect.bottom - 40 && rect.bottom > rootRect.top + 40;
    if (!visible) {
      scrollToPage(currentPage, "start");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- header/thumbnail page jumps
  }, [currentPage]);

  return (
    <div className="relative flex h-full min-h-0 flex-col bg-zinc-100">
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-4 overflow-auto p-4">
        {pages.map((page) => (
          <PageView
            key={page.pageNumber}
            page={page}
            filename={filename}
            selectedId={selectedId}
            onSelect={onSelect}
            pageRef={(el) => {
              pageRefs.current[page.pageNumber] = el;
            }}
            zoomPercent={zoomPercent}
          />
        ))}
      </div>

      {showThumbnails ? <div className="border-t border-zinc-200 bg-white px-3 py-2">
        <div className="text-xs font-medium text-zinc-500">
          Pages ({pages.length})
        </div>
        <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
          {pages.map((page) => {
            const active = page.pageNumber === currentPage;
            return (
              <button
                key={page.pageNumber}
                type="button"
                onClick={() => scrollToPage(page.pageNumber)}
                className={`shrink-0 overflow-hidden rounded border-2 ${
                  active ? "border-emerald-400" : "border-transparent ring-1 ring-zinc-200"
                }`}
              >
                <img
                  src={resolveImageUrl(page.imageUrl)}
                  alt={`page ${page.pageNumber}`}
                  className="h-16 w-12 object-cover"
                />
              </button>
            );
          })}
        </div>
      </div> : null}
    </div>
  );
}
