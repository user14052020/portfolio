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
    <div className="max-w-[680px]">
      <div
        className="inline-flex items-center gap-1.5 rounded-[28px] rounded-tl-lg border border-white/80 bg-white/88 px-5 py-4 shadow-[var(--shadow-soft-sm)]"
        role="status"
        aria-label={ariaLabel}
      >
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-[var(--text-muted)]" />
        <span
          className="h-2.5 w-2.5 animate-bounce rounded-full bg-[var(--text-muted)]"
          style={{ animationDelay: "120ms" }}
        />
        <span
          className="h-2.5 w-2.5 animate-bounce rounded-full bg-[var(--text-muted)]"
          style={{ animationDelay: "240ms" }}
        />
      </div>
    </div>
  );
}
