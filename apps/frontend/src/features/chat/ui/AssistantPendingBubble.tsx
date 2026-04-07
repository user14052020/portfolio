"use client";

import type { Locale } from "@/shared/api/types";

export function AssistantPendingBubble({
  locale,
  isGenerationIntent: _isGenerationIntent
}: {
  locale: Locale;
  isGenerationIntent: boolean;
}) {
  const ariaLabel = locale === "ru" ? "Ассистент печатает" : "Assistant is typing";

  return (
    <div className="max-w-[620px]">
      <div
        className="inline-flex items-center gap-1.5 py-1"
        role="status"
        aria-label={ariaLabel}
      >
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-slate-400" />
        <span
          className="h-2.5 w-2.5 animate-bounce rounded-full bg-slate-400"
          style={{ animationDelay: "120ms" }}
        />
        <span
          className="h-2.5 w-2.5 animate-bounce rounded-full bg-slate-400"
          style={{ animationDelay: "240ms" }}
        />
      </div>
    </div>
  );
}
