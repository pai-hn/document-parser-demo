import {
  ChevronDown,
  FileSpreadsheet,
  FileText,
  FolderOpen,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  cacheDetectionResult,
  detectSample,
  detectUpload,
  listSamples,
} from "@/api/client";
import { AppSidebar } from "@/components/AppSidebar";
import { FeatureButtons } from "@/components/parser/FeatureButtons";
import type { SampleProject } from "@/types/document";

export function HomePage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [samples, setSamples] = useState<SampleProject[]>([]);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"recent" | "examples">("recent");
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  useEffect(() => {
    void listSamples().then(setSamples);
  }, []);

  const openResult = useCallback(
    async (runner: () => Promise<Awaited<ReturnType<typeof detectUpload>>>) => {
      setLoading(true);
      setError(null);
      try {
        const result = await runner();
        cacheDetectionResult(result);
        navigate(`/documents/${result.documentId}`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Detection failed");
      } finally {
        setLoading(false);
      }
    },
    [navigate],
  );

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;
    setPendingFile(file);
  };

  const handleParse = () => {
    if (pendingFile) {
      void openResult(() => detectUpload(pendingFile));
      return;
    }
    if (samples[0]) {
      void openResult(() => detectSample(samples[0].sampleId));
    }
  };

  return (
    <div className="flex h-full min-h-screen bg-[#f7f7f8]">
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-zinc-200/80 bg-white px-6 py-3">
          <div className="flex items-center gap-4">
            <div className="text-lg font-semibold tracking-tight">Publicai</div>
            <button
              type="button"
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-sm text-zinc-600 hover:bg-zinc-100"
            >
              Explore
              <ChevronDown className="h-3.5 w-3.5" />
            </button>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-800">
              798.4 free credits left
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded-full bg-zinc-900 px-4 py-1.5 text-sm font-medium text-white"
            >
              Upgrade
            </button>
            <button type="button" className="text-sm text-zinc-600 hover:text-zinc-900">
              Check API Doc
            </button>
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-100 text-zinc-600"
              aria-label="Settings"
            >
              <Sparkles className="h-4 w-4" />
            </button>
          </div>
        </header>

        <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-10">
          <div className="text-center">
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
              Turn Documents into Trusted Data
            </h1>
            <p className="mt-2 text-sm text-zinc-500">
              Upload a page image, run detection, and edit structured markdown side by side.
            </p>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              handleFiles(e.dataTransfer.files);
            }}
            onClick={() => inputRef.current?.click()}
            className={`cursor-pointer rounded-2xl border-2 border-dashed bg-white px-6 py-14 text-center transition ${
              dragging
                ? "border-emerald-400 bg-emerald-50/40"
                : "border-zinc-300 hover:border-zinc-400"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif,.pdf,.png,.jpg,.jpeg,.webp"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <div className="mb-4 flex items-center justify-center gap-3 text-zinc-400">
              <FileText className="h-8 w-8 text-rose-400" />
              <FileText className="h-8 w-8 text-sky-500" />
              <FileSpreadsheet className="h-8 w-8 text-emerald-500" />
            </div>
            <div className="text-base font-medium text-zinc-800">
              {pendingFile ? pendingFile.name : "Upload files"}
            </div>
            <p className="mt-1 text-sm text-zinc-500">
              Choose files or drag them here. JPG, PNG, WEBP, PDF (전체 페이지 파싱)
            </p>
          </div>

          <div className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white px-4 py-3 shadow-sm">
            <select
              className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm outline-none"
              defaultValue="dpt-3-pro"
            >
              <option value="dpt-3-pro">DPT-3 Pro</option>
              <option value="dpt-2">DPT-2</option>
            </select>
            <button
              type="button"
              disabled={loading}
              onClick={handleParse}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-200 px-5 py-2 text-sm font-semibold text-emerald-900 transition hover:bg-emerald-300 disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Parse
            </button>
          </div>

          <FeatureButtons onParse={handleParse} />

          {error ? (
            <p className="text-center text-sm text-rose-600">{error}</p>
          ) : null}

          <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex gap-4 border-b border-zinc-100 px-1 text-sm">
              <button
                type="button"
                onClick={() => setTab("recent")}
                className={`pb-2 ${
                  tab === "recent"
                    ? "border-b-2 border-zinc-900 font-medium text-zinc-900"
                    : "text-zinc-400"
                }`}
              >
                Recent Projects
              </button>
              <button
                type="button"
                onClick={() => setTab("examples")}
                className={`pb-2 ${
                  tab === "examples"
                    ? "border-b-2 border-zinc-900 font-medium text-zinc-900"
                    : "text-zinc-400"
                }`}
              >
                Examples
              </button>
            </div>

            <ul className="divide-y divide-zinc-100">
              {samples.map((sample) => (
                <li key={sample.sampleId}>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => void openResult(() => detectSample(sample.sampleId))}
                    className="flex w-full items-center gap-3 px-2 py-3 text-left transition hover:bg-zinc-50 disabled:opacity-60"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-100 text-zinc-500">
                      <FolderOpen className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-zinc-800">
                        {sample.title}
                      </div>
                      <div className="text-xs text-zinc-400">{sample.fileCount} file</div>
                    </div>
                    <img
                      src={sample.thumbnailUrl}
                      alt=""
                      className="h-10 w-8 rounded object-cover ring-1 ring-zinc-200"
                    />
                  </button>
                </li>
              ))}
            </ul>
            <div className="pt-3 text-center">
              <button type="button" className="text-sm text-zinc-500 hover:text-zinc-800">
                View All Projects
              </button>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
