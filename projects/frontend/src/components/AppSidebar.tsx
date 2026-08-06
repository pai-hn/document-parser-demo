import {
  CalendarDays,
  CreditCard,
  Cuboid,
  Folder,
  KeyRound,
  LineChart,
  Phone,
  Plus,
  Sparkles,
  Upload,
} from "lucide-react";
import { Link } from "react-router-dom";

const NAV_ICONS = [
  Folder,
  Cuboid,
  KeyRound,
  CreditCard,
  LineChart,
  CalendarDays,
  Phone,
] as const;

export function AppSidebar() {
  return (
    <aside className="flex h-full w-14 shrink-0 flex-col items-center border-r border-zinc-200 bg-white py-3">
      <Link
        to="/"
        className="mb-4 flex h-9 w-9 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"
        aria-label="Home"
      >
        <Plus className="h-5 w-5" strokeWidth={2.25} />
      </Link>

      <nav className="flex flex-1 flex-col items-center gap-3 text-zinc-400">
        {NAV_ICONS.map((Icon, i) => (
          <button
            key={i}
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-xl transition hover:bg-zinc-100 hover:text-zinc-600"
            aria-label={`nav-${i}`}
          >
            <Icon className="h-5 w-5" />
          </button>
        ))}
      </nav>

      <div className="mt-auto flex flex-col items-center gap-3">
        <button
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"
          aria-label="Upload"
        >
          <Upload className="h-4 w-4" />
        </button>
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500 text-white">
          <Sparkles className="h-4 w-4" />
        </div>
      </div>
    </aside>
  );
}
