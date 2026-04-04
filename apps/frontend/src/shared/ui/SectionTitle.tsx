import { cn } from "@/shared/lib/cn";

export function SectionTitle({
  eyebrow,
  title,
  subtitle,
  className
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  className?: string;
}) {
  return (
    <div className={cn("max-w-3xl space-y-3", className)}>
      <p className="font-mono text-xs uppercase tracking-[0.28em] text-slate-500">{eyebrow}</p>
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900 md:text-5xl">{title}</h2>
      {subtitle ? <p className="text-base leading-7 text-slate-600 md:text-lg">{subtitle}</p> : null}
    </div>
  );
}

