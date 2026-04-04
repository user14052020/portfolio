import { cn } from "@/shared/lib/cn";

export function WindowFrame({
  title,
  subtitle,
  children,
  className
}: {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.07)]",
        className
      )}
    >
      {title || subtitle ? (
        <div className="border-b border-slate-200 px-5 py-4">
          <div className="space-y-1">
            {title ? <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-slate-400">{title}</p> : null}
            {subtitle ? <p className="text-xs text-slate-500">{subtitle}</p> : null}
          </div>
        </div>
      ) : null}
      <div className="p-5 md:p-7">{children}</div>
    </section>
  );
}
