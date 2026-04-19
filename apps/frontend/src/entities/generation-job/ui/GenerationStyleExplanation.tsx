"use client";

import type { GenerationJob, Locale } from "@/shared/api/types";

function buildExplanationLines(job: GenerationJob | null) {
  const explanation = job?.style_explanation;
  if (!explanation) {
    return [];
  }

  const lines: string[] = [];
  if (typeof explanation.short_explanation === "string" && explanation.short_explanation.trim()) {
    lines.push(explanation.short_explanation.trim());
  }
  if (
    typeof explanation.supporting_text === "string" &&
    explanation.supporting_text.trim() &&
    !lines.includes(explanation.supporting_text.trim())
  ) {
    lines.push(explanation.supporting_text.trim());
  }
  for (const item of explanation.distinct_points ?? []) {
    const cleaned = typeof item === "string" ? item.trim() : "";
    if (cleaned && !lines.includes(cleaned)) {
      lines.push(cleaned);
    }
    if (lines.length >= 4) {
      break;
    }
  }
  return lines.slice(0, 4);
}

export function GenerationStyleExplanation({
  job,
  locale,
}: {
  job: GenerationJob | null;
  locale: Locale;
}) {
  const explanation = job?.style_explanation;
  const title = typeof explanation?.style_name === "string" ? explanation.style_name.trim() : "";
  const lines = buildExplanationLines(job);

  if (!title && lines.length === 0) {
    return null;
  }

  return (
    <div className="rounded-[24px] border border-[#e7d7bf] bg-[#f8f4ed]/95 px-4 py-3 shadow-sm">
      <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">
        {locale === "ru" ? "О стиле" : "About the style"}
      </p>
      {title ? <p className="mt-2 text-sm font-medium text-slate-900">{title}</p> : null}
      {lines.length > 0 ? (
        <div className="mt-2 space-y-2">
          {lines.map((line) => (
            <p key={line} className="text-sm leading-6 text-slate-700">
              {line}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
