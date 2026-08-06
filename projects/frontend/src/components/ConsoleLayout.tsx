import type { ReactNode } from "react";
import { Link } from "react-router-dom";

const NAV_ITEMS = ["서비스", "운영 개요", "모델", "바인딩", "지식", "PDF 분석", "모니터링", "설정"];

interface ConsoleLayoutProps {
  children: ReactNode;
}

export function ConsoleLayout({ children }: ConsoleLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col bg-[#edf2f8] text-slate-900">
      <header className="flex h-10 items-center bg-[#073b78] px-5 text-white">
        <Link to="/" className="flex items-center gap-2 font-bold">
          <span className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-white bg-[#e5243b] text-[10px]">
            AI
          </span>
          <span>지방세 AI 운영 콘솔</span>
        </Link>
        <span className="ml-3 rounded bg-white/15 px-2 py-0.5 text-xs font-semibold">gov 채널</span>
        <span className="ml-1 rounded bg-white/15 px-2 py-0.5 text-xs font-semibold">공무원 전용</span>
        <div className="ml-auto flex items-center gap-2 text-sm font-semibold">
          <span>admin</span>
          <button type="button" className="rounded bg-white/15 px-2.5 py-1 text-xs">로그아웃</button>
        </div>
      </header>
      <nav className="flex h-10 items-end gap-1 border-b border-slate-200 bg-white px-5">
        {NAV_ITEMS.map((item) => (
          <button
            key={item}
            type="button"
            className={`h-full border-b-2 px-3 text-sm font-medium ${
              item === "PDF 분석"
                ? "border-blue-600 text-blue-700"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            {item}
          </button>
        ))}
      </nav>
      {children}
    </div>
  );
}

export function ConsolePageHeading({ actions }: { actions?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-bold tracking-tight">PDF Detection 모니터링</h1>
        <p className="mt-0.5 text-xs text-slate-600">
          PyMuPDF 휴리스틱 분류 결과이며 모델 정확도가 아닙니다.
        </p>
      </div>
      {actions ? <div className="flex gap-2">{actions}</div> : null}
    </div>
  );
}

export const primaryButtonClass =
  "inline-flex h-9 items-center justify-center gap-2 rounded bg-blue-600 px-4 text-sm font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300";
