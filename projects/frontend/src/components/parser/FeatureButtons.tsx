import {
  FileSearch,
  LayoutGrid,
  PanelTop,
  ScanText,
  Scissors,
} from "lucide-react";

const FEATURES = [
  {
    id: "parse",
    label: "Parse",
    description: "Extract structured content",
    icon: ScanText,
    className: "bg-emerald-50 text-emerald-700 ring-emerald-100",
  },
  {
    id: "extract",
    label: "Extract",
    description: "Pull key fields",
    icon: FileSearch,
    className: "bg-sky-50 text-sky-700 ring-sky-100",
  },
  {
    id: "split",
    label: "Split",
    description: "Split by section",
    icon: Scissors,
    className: "bg-orange-50 text-orange-700 ring-orange-100",
  },
  {
    id: "classify",
    label: "Classify",
    description: "Label document type",
    icon: LayoutGrid,
    className: "bg-stone-100 text-stone-600 ring-stone-200",
  },
  {
    id: "section",
    label: "Section",
    description: "Detect sections",
    icon: PanelTop,
    className: "bg-rose-50 text-rose-700 ring-rose-100",
  },
] as const;

interface FeatureButtonsProps {
  onParse?: () => void;
}

export function FeatureButtons({ onParse }: FeatureButtonsProps) {
  return (
    <div className="mx-auto grid w-full max-w-3xl grid-cols-2 gap-3 sm:grid-cols-5">
      {FEATURES.map((feature) => {
        const Icon = feature.icon;
        const interactive = feature.id === "parse" && onParse;
        return (
          <button
            key={feature.id}
            type="button"
            onClick={interactive ? onParse : undefined}
            className={`flex flex-col items-start gap-2 rounded-2xl p-4 text-left ring-1 transition hover:brightness-[0.98] ${feature.className}`}
          >
            <Icon className="h-5 w-5" />
            <div>
              <div className="text-sm font-semibold">{feature.label}</div>
              <div className="mt-0.5 text-[11px] opacity-70">{feature.description}</div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
