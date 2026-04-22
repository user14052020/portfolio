import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type PillBadgeTone = "neutral" | "accent" | "subtle" | "mint" | "rose" | "lilac" | "dark" | "warning" | "success";
type PillBadgeSize = "sm" | "md";

const toneClasses: Record<PillBadgeTone, string> = {
  neutral: "border-[var(--border-soft)] bg-white/80 text-[var(--text-secondary)]",
  accent: "border-[#ead6b8] bg-[#fff8ef] text-[#7f5424]",
  subtle: "border-transparent bg-[var(--surface-secondary)] text-[var(--text-secondary)]",
  mint: "border-emerald-200 bg-[var(--surface-mint)] text-emerald-800",
  rose: "border-rose-200 bg-[var(--surface-rose)] text-rose-800",
  lilac: "border-violet-200 bg-[var(--surface-lilac)] text-violet-800",
  dark: "border-[var(--border-inverse)] bg-[var(--surface-ink)] text-[var(--text-inverse)]",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
};

const sizeClasses: Record<PillBadgeSize, string> = {
  sm: "px-3 py-1 text-[11px]",
  md: "px-3.5 py-1.5 text-xs",
};

export function PillBadge({
  tone = "neutral",
  size = "md",
  children,
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & {
  tone?: PillBadgeTone;
  size?: PillBadgeSize;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-[var(--radius-pill)] border font-semibold uppercase tracking-[0.18em]",
        toneClasses[tone],
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
