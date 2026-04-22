import type { ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type SurfaceCardVariant = "default" | "tinted" | "elevated" | "soft" | "ink";
type SurfaceCardPadding = "none" | "sm" | "md" | "lg";

const variantClasses: Record<SurfaceCardVariant, string> = {
  default: "border-[var(--border-soft)] bg-[var(--surface-primary)] text-[var(--text-primary)] shadow-[var(--shadow-soft-sm)]",
  tinted:
    "border-[var(--border-soft)] bg-[linear-gradient(135deg,var(--surface-elevated),var(--surface-secondary))] text-[var(--text-primary)] shadow-[var(--shadow-soft-md)]",
  elevated: "border-white/80 bg-[var(--surface-elevated)] text-[var(--text-primary)] shadow-[var(--shadow-soft-xl)]",
  soft: "border-[var(--border-soft)] bg-white/60 text-[var(--text-primary)] shadow-[var(--shadow-soft-sm)] backdrop-blur",
  ink: "border-[var(--border-inverse)] bg-[var(--surface-ink)] text-[var(--text-inverse)] shadow-[var(--shadow-soft-xl)]",
};

const paddingClasses: Record<SurfaceCardPadding, string> = {
  none: "",
  sm: "p-4",
  md: "p-5 md:p-6",
  lg: "p-6 md:p-8",
};

export function SurfaceCard({
  children,
  className,
  variant = "default",
  padding = "md",
  header,
  footer,
}: {
  children: ReactNode;
  className?: string;
  variant?: SurfaceCardVariant;
  padding?: SurfaceCardPadding;
  header?: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-[var(--radius-panel)] border",
        variantClasses[variant],
        className,
      )}
    >
      {header ? <div className="border-b border-[var(--border-soft)] px-5 py-4 md:px-6">{header}</div> : null}
      <div className={paddingClasses[padding]}>{children}</div>
      {footer ? <div className="border-t border-[var(--border-soft)] px-5 py-4 md:px-6">{footer}</div> : null}
    </section>
  );
}
