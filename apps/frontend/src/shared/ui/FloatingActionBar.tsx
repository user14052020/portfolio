import type { ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type FloatingActionBarVariant = "floating" | "inline" | "dark";

const variantClasses: Record<FloatingActionBarVariant, string> = {
  floating:
    "border-[var(--border-soft)] bg-white/80 text-[var(--text-primary)] shadow-[var(--shadow-soft-xl)] backdrop-blur-xl",
  inline: "border-[var(--border-soft)] bg-[var(--surface-primary)] text-[var(--text-primary)] shadow-[var(--shadow-soft-sm)]",
  dark: "border-[var(--border-inverse)] bg-[var(--surface-ink)] text-[var(--text-inverse)] shadow-[var(--shadow-soft-xl)]",
};

export function FloatingActionBar({
  children,
  className,
  variant = "floating",
}: {
  children: ReactNode;
  className?: string;
  variant?: FloatingActionBarVariant;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-center gap-2 rounded-[var(--radius-pill)] border px-3 py-2",
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </div>
  );
}
