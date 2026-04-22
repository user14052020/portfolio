import type { ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type SectionHeaderAlign = "left" | "center";
type SectionHeaderSize = "md" | "lg";

export function SectionHeader({
  eyebrow,
  title,
  description,
  action,
  align = "left",
  size = "md",
  className,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  align?: SectionHeaderAlign;
  size?: SectionHeaderSize;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-5 md:flex-row md:items-end md:justify-between",
        align === "center" && "items-center text-center md:flex-col md:items-center md:justify-start",
        className,
      )}
    >
      <div className={cn("max-w-3xl space-y-3", align === "center" && "mx-auto")}>
        {eyebrow ? (
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--text-muted)]">{eyebrow}</p>
        ) : null}
        <h2
          className={cn(
            "font-display text-[var(--text-primary)]",
            size === "lg" ? "text-4xl leading-[1.02] md:text-6xl" : "text-3xl leading-tight md:text-4xl",
          )}
        >
          {title}
        </h2>
        {description ? (
          <p className="max-w-2xl text-base leading-7 text-[var(--text-secondary)] md:text-lg">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
