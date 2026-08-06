import { Copy, Download, Search, Settings2 } from "lucide-react";
import { useEffect, useRef } from "react";
import { BBOX_COLORS } from "@/lib/bboxColors";
import type { DetectionBlock } from "@/types/document";

type ViewMode = "markdown" | "json";

interface MarkdownPanelProps {
  blocks: DetectionBlock[];
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  selectedId: string | null;
  onSelect: (blockId: string) => void;
  onBlockChange: (blockId: string, markdown: string) => void;
}

export function MarkdownPanel({
  blocks,
  viewMode,
  onViewModeChange,
  selectedId,
  onSelect,
  onBlockChange,
}: MarkdownPanelProps) {
  const itemRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!selectedId) return;
    const el = itemRefs.current[selectedId];
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [selectedId]);

  let lastPage = -1;

  return (
    <div className="flex h-full min-h-0 flex-col border-l border-zinc-200 bg-white">
      <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-2">
        <div className="flex gap-1 rounded-lg bg-zinc-100 p-0.5 text-sm">
          {(["markdown", "json"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => onViewModeChange(mode)}
              className={`rounded-md px-3 py-1.5 capitalize transition ${
                viewMode === mode
                  ? "bg-white font-medium text-zinc-900 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-800"
              }`}
            >
              {mode === "markdown" ? "Markdown" : "JSON"}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 text-zinc-500">
          <button type="button" className="rounded-md p-1.5 hover:bg-zinc-100" aria-label="Search">
            <Search className="h-4 w-4" />
          </button>
          <button type="button" className="rounded-md p-1.5 hover:bg-zinc-100" aria-label="Download">
            <Download className="h-4 w-4" />
          </button>
          <button type="button" className="rounded-md p-1.5 hover:bg-zinc-100" aria-label="Copy">
            <Copy className="h-4 w-4" />
          </button>
          <button
            type="button"
            className="ml-1 flex items-center gap-1 rounded-md px-2 py-1 text-xs hover:bg-zinc-100"
          >
            <Settings2 className="h-3.5 w-3.5" />
            Display
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
        {viewMode === "json" ? (
          <pre className="overflow-x-auto rounded-lg bg-zinc-50 p-3 text-xs leading-relaxed text-zinc-700">
            {JSON.stringify(blocks, null, 2)}
          </pre>
        ) : (
          <div className="space-y-4">
            {blocks.map((block) => {
              const color = BBOX_COLORS[block.type] ?? "#22C55E";
              const selected = selectedId === block.id;
              const showPageHeader = block.page !== lastPage;
              lastPage = block.page;
              return (
                <div key={block.id}>
                  {showPageHeader ? (
                    <div className="mb-2 mt-1 text-xs font-semibold uppercase tracking-wide text-zinc-400">
                      Page {block.page}
                    </div>
                  ) : null}
                  <div
                    ref={(el) => {
                      itemRefs.current[block.id] = el;
                    }}
                    data-block-id={block.id}
                    onClick={() => onSelect(block.id)}
                    className={`rounded-xl border p-3 transition ${
                      selected
                        ? "border-transparent shadow-sm"
                        : "border-zinc-200 hover:border-zinc-300"
                    }`}
                    style={
                      selected
                        ? { borderColor: color, boxShadow: `0 0 0 1px ${color}55` }
                        : undefined
                    }
                  >
                    <div className="mb-2 flex items-center gap-2">
                      <span
                        className="rounded px-1.5 py-0.5 text-[11px] font-semibold text-white"
                        style={{ backgroundColor: color }}
                      >
                        {block.index} -{" "}
                        {block.type.charAt(0).toUpperCase() + block.type.slice(1)}
                      </span>
                    </div>
                    <textarea
                      value={block.markdown}
                      onChange={(e) => onBlockChange(block.id, e.target.value)}
                      onFocus={() => onSelect(block.id)}
                      rows={Math.min(12, Math.max(3, block.markdown.split("\n").length + 1))}
                      className="w-full resize-y rounded-lg border border-zinc-200 bg-zinc-50/80 px-3 py-2 font-mono text-sm leading-relaxed text-zinc-800 outline-none focus:border-zinc-400 focus:bg-white"
                    />
                    {block.html ? (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-xs text-zinc-500">HTML</summary>
                        <pre className="mt-1 max-h-40 overflow-auto rounded-lg bg-zinc-100 p-2 text-[11px] text-zinc-700">
                          {block.html}
                        </pre>
                      </details>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
