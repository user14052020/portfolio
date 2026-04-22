import type { ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type WindowFrameVariant = "default" | "tinted" | "elevated" | "chat" | "admin";
type WindowFrameDecorativeTone = "none" | "lilac" | "rose" | "mint" | "sand" | "ink";

const variantClasses: Record<WindowFrameVariant, string> = {
  default:
    "border-[var(--border-soft)] bg-[var(--surface-primary)] shadow-[var(--shadow-soft-md)]",
  tinted:
    "border-[var(--border-soft)] bg-[linear-gradient(135deg,var(--surface-elevated),var(--surface-secondary))] shadow-[var(--shadow-soft-md)]",
  elevated:
    "border-white/80 bg-[var(--surface-elevated)] shadow-[var(--shadow-soft-xl)]",
  chat:
    "border-white/75 bg-[var(--surface-primary)] shadow-[var(--shadow-soft-xl)]",
  admin:
    "border-[var(--border-strong)] bg-[linear-gradient(135deg,#ffffff,var(--surface-secondary))] shadow-[var(--shadow-soft-md)]",
};

const decorativeToneClasses: Record<WindowFrameDecorativeTone, string> = {
  none: "",
  lilac: "after:bg-[radial-gradient(circle_at_20%_0%,rgba(239,237,255,0.82),transparent_22rem)]",
  rose: "after:bg-[radial-gradient(circle_at_18%_0%,rgba(253,239,245,0.9),transparent_22rem)]",
  mint: "after:bg-[radial-gradient(circle_at_18%_0%,rgba(234,247,239,0.9),transparent_22rem)]",
  sand: "after:bg-[radial-gradient(circle_at_18%_0%,rgba(248,241,232,0.95),transparent_22rem)]",
  ink: "after:bg-[radial-gradient(circle_at_18%_0%,rgba(20,20,22,0.08),transparent_22rem)]",
};

export function WindowFrame({
  title,
  subtitle,
  action,
  footer,
  variant = "default",
  decorativeTone = "none",
  children,
  className,
  headerClassName,
  bodyClassName,
  footerClassName,
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  footer?: ReactNode;
  variant?: WindowFrameVariant;
  decorativeTone?: WindowFrameDecorativeTone;
  children: ReactNode;
  className?: string;
  headerClassName?: string;
  bodyClassName?: string;
  footerClassName?: string;
}) {
  const hasHeader = Boolean(title || subtitle || action);

  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-[var(--radius-panel)] border",
        "after:pointer-events-none after:absolute after:inset-0 after:z-0 after:opacity-80",
        variantClasses[variant],
        decorativeToneClasses[decorativeTone],
        className
      )}
    >
      {hasHeader ? (
        <div
          className={cn(
            "relative z-10 flex items-start justify-between gap-4 border-b border-[var(--border-soft)] px-5 py-4 md:px-6",
            headerClassName,
          )}
        >
          <div className="space-y-1">
            {title ? (
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--text-muted)]">{title}</p>
            ) : null}
            {subtitle ? <p className="text-sm leading-5 text-[var(--text-secondary)]">{subtitle}</p> : null}
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>
      ) : null}
      <div className={cn("relative z-10 p-5 md:p-7", bodyClassName)}>{children}</div>
      {footer ? (
        <div
          className={cn(
            "relative z-10 border-t border-[var(--border-soft)] px-5 py-4 md:px-6",
            footerClassName,
          )}
        >
          {footer}
        </div>
      ) : null}
    </section>
  );
}
