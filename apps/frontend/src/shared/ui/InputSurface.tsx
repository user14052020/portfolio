"use client";

import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type InputSurfaceTone = "default" | "muted" | "elevated" | "dark";
type InputSurfaceDensity = "compact" | "comfortable" | "spacious";
type InputSurfaceActionTone = "default" | "dark";

const toneClasses: Record<InputSurfaceTone, string> = {
  default: "border-[var(--border-soft)] bg-white/92 text-[var(--text-primary)] shadow-[var(--shadow-soft-sm)]",
  muted: "border-[var(--border-soft)] bg-[var(--surface-secondary)] text-[var(--text-primary)] shadow-none",
  elevated: "border-white/80 bg-[var(--surface-elevated)] text-[var(--text-primary)] shadow-[var(--shadow-soft-md)]",
  dark: "border-[var(--border-inverse)] bg-[var(--surface-ink)] text-[var(--text-inverse)] shadow-[var(--shadow-soft-md)]",
};

const densityClasses: Record<InputSurfaceDensity, string> = {
  compact: "px-3 py-2.5",
  comfortable: "px-4 py-3.5",
  spacious: "px-5 py-4",
};

export function InputSurface({
  children,
  className,
  bodyClassName,
  footerClassName,
  disabled = false,
  tone = "default",
  density = "comfortable",
  action,
  actionTone = "default",
  chips,
  footer,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  bodyClassName?: string;
  footerClassName?: string;
  disabled?: boolean;
  tone?: InputSurfaceTone;
  density?: InputSurfaceDensity;
  action?: ReactNode;
  actionTone?: InputSurfaceActionTone;
  chips?: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-panel)] border transition duration-200",
        toneClasses[tone],
        densityClasses[density],
        disabled && "cursor-not-allowed border-slate-200 bg-slate-50/90 text-slate-400 shadow-none opacity-80",
        className,
      )}
      {...props}
    >
      {chips ? <div className="mb-3 flex flex-wrap gap-2">{chips}</div> : null}
      {action ? (
        <div className={cn("flex items-end gap-3", bodyClassName)}>
          <div className="min-w-0 flex-1">{children}</div>
          <div
            className={cn(
              "shrink-0",
              actionTone === "dark" && "rounded-[var(--radius-pill)] bg-[var(--surface-ink)] text-[var(--text-inverse)]",
            )}
          >
            {action}
          </div>
        </div>
      ) : (
        <div className={bodyClassName}>{children}</div>
      )}
      {footer ? (
        <div
          className={cn(
            "mt-3 border-t border-[var(--border-soft)] pt-3 text-sm text-[var(--text-secondary)]",
            footerClassName,
          )}
        >
          {footer}
        </div>
      ) : null}
    </div>
  );
}
