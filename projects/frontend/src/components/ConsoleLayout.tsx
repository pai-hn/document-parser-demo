import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { Moon } from "lucide-react";
import { GovEmblem } from "@/components/GovEmblem";

const SERVICE_NAME = "지방세 AI 운영 콘솔";
const CHANNEL_BADGE = "대국민 서비스";

type NavItem = { id: string; label: string; dividerAfter?: boolean };

/** 스크린샷 IA — 실기능은 서비스(PDF)만, 나머지는 mock */
const NAV_ITEMS: NavItem[] = [
  { id: "service", label: "서비스" },
  { id: "overview", label: "운영 개요", dividerAfter: true },
  { id: "region", label: "권역" },
  { id: "models", label: "모델" },
  { id: "bindings", label: "바인딩" },
  { id: "knowledge", label: "지식" },
  { id: "monitoring", label: "모니터링" },
  { id: "voice", label: "음성" },
  { id: "settings", label: "설정" },
];

function isServiceRoute(pathname: string): boolean {
  return pathname === "/" || pathname.startsWith("/documents");
}

interface ConsoleLayoutProps {
  children: ReactNode;
}

export function ConsoleLayout({ children }: ConsoleLayoutProps) {
  const { pathname } = useLocation();
  const activeId = isServiceRoute(pathname) ? "service" : null;

  return (
    <div className="flex min-h-screen flex-col bg-canvas text-ink">
      <header className="sticky top-0 z-50">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 bg-brand-navy px-4 py-2 text-white">
          <Link
            to="/"
            className="flex items-center gap-2 rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
          >
            <GovEmblem className="size-6 shrink-0" />
            <span className="font-bold">{SERVICE_NAME}</span>
          </Link>
          <span className="inline-flex items-center rounded-sm bg-white/15 px-1.5 py-0.5 text-xs font-semibold">
            {CHANNEL_BADGE}
          </span>
          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              aria-label="테마"
              className="flex size-7 items-center justify-center rounded-full border border-white/30 text-white/90 hover:bg-white/10"
            >
              <Moon className="size-3.5" strokeWidth={2} />
            </button>
            <span className="text-sm font-semibold">admin</span>
            <button
              type="button"
              className="rounded-sm bg-white/10 px-2.5 py-1 text-xs font-semibold hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
            >
              로그아웃
            </button>
          </div>
        </div>
        <nav
          aria-label="주 메뉴"
          className="flex items-center gap-0.5 overflow-x-auto border-b border-line bg-surface px-3"
        >
          {NAV_ITEMS.map((item) => (
            <span key={item.id} className="flex items-center">
              <button
                type="button"
                className={`flex min-h-10 items-center border-b-[3px] px-3 text-sm font-semibold whitespace-nowrap transition-colors ${
                  activeId === item.id
                    ? "border-primary text-primary"
                    : "border-transparent text-ink-muted hover:text-ink"
                }`}
              >
                {item.label}
              </button>
              {item.dividerAfter ? (
                <span aria-hidden="true" className="mx-1 h-4 w-px shrink-0 bg-line" />
              ) : null}
            </span>
          ))}
        </nav>
      </header>
      {children}
    </div>
  );
}

export function ConsolePageHeading({ actions }: { actions?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-bold tracking-tight">PDF Detection 모니터링</h1>
        <p className="mt-0.5 text-xs text-ink-muted">
          PyMuPDF 휴리스틱 분류 결과이며 모델 정확도가 아닙니다.
        </p>
      </div>
      {actions ? <div className="flex gap-2">{actions}</div> : null}
    </div>
  );
}

export const primaryButtonClass =
  "inline-flex h-9 items-center justify-center gap-2 rounded bg-primary px-4 text-sm font-bold text-white transition hover:bg-primary-strong disabled:cursor-not-allowed disabled:bg-slate-300";
