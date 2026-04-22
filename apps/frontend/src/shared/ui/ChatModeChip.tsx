import { cn } from "@/shared/lib/cn";

type ChatModeChipTone = "online" | "generating" | "offline" | "locked" | "neutral";

const toneClasses: Record<ChatModeChipTone, string> = {
  online: "border-emerald-200 bg-emerald-50 text-emerald-800",
  generating: "border-amber-200 bg-amber-50 text-amber-800",
  offline: "border-rose-200 bg-rose-50 text-rose-800",
  locked: "border-slate-300 bg-slate-100 text-slate-700",
  neutral: "border-[var(--border-soft)] bg-white/80 text-[var(--text-secondary)]",
};

export function ChatModeChip({
  label,
  tone = "neutral",
  className,
}: {
  label: string;
  tone?: ChatModeChipTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-[var(--radius-pill)] border px-3 py-1 text-xs font-semibold",
        toneClasses[tone],
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {label}
    </span>
  );
}
