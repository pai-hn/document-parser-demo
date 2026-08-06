import { FileText, Loader2, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { cacheDetectionResult, detectUpload } from "@/api/client";
import { ConsoleLayout, ConsolePageHeading, primaryButtonClass } from "@/components/ConsoleLayout";

function isPdf(file: File): boolean {
  return file.type === "application/pdf" && file.name.toLowerCase().endsWith(".pdf");
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function HomePage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectFile = (candidate?: File) => {
    setError(null);
    if (!candidate) return;
    if (!isPdf(candidate)) {
      setFile(null);
      setError("PDF 파일만 업로드할 수 있습니다.");
      return;
    }
    setFile(candidate);
  };

  const analyze = async () => {
    if (!file || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await detectUpload(file);
      cacheDetectionResult(result);
      navigate(`/documents/${result.documentId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "PDF 분석에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ConsoleLayout>
      <main className="flex flex-1 flex-col gap-4 p-3">
        <ConsolePageHeading
          actions={
            <button type="button" disabled={!file || loading} onClick={() => void analyze()} className={primaryButtonClass}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {loading ? "분석 중" : "분석 시작"}
            </button>
          }
        />
        <section className="flex min-h-[520px] flex-1 flex-col rounded border border-slate-200 bg-white p-8 shadow-sm">
          <button
            type="button"
            disabled={loading}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); selectFile(e.dataTransfer.files[0]); }}
            className={`flex flex-1 flex-col items-center justify-center rounded-2xl border-2 border-dashed px-8 text-center transition ${
              dragging ? "border-blue-500 bg-blue-50" : "border-slate-400 bg-slate-50/30 hover:border-blue-500 hover:bg-blue-50/40"
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(e) => selectFile(e.target.files?.[0])}
            />
            {file ? (
              <>
                <FileText className="h-14 w-14 text-red-500" />
                <strong className="mt-5 text-xl">{file.name}</strong>
                <span className="mt-2 text-sm text-slate-500">{formatBytes(file.size)} · PDF</span>
                <span className="mt-4 text-sm font-medium text-blue-700">다른 PDF 선택</span>
              </>
            ) : (
              <>
                <UploadCloud className="h-16 w-16 text-blue-600" strokeWidth={1.5} />
                <strong className="mt-5 text-2xl">PDF 업로드</strong>
                <span className="mt-3 text-lg text-slate-500">PDF 파일을 선택하거나 여기로 드래그하세요. (전체 페이지 분석)</span>
              </>
            )}
          </button>
          {error ? <p role="alert" className="mt-4 text-center text-sm font-medium text-red-600">{error}</p> : null}
        </section>
      </main>
    </ConsoleLayout>
  );
}
