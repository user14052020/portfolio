"use client";

import type { GenerationJobState } from "@/entities/generation-job/model/types";
import { GenerationStatusRail } from "@/features/chat/ui/GenerationStatusRail";
import type { Locale } from "@/shared/api/types";

function formatSecondsLabel(locale: "ru" | "en", seconds: number) {
  if (seconds <= 0) {
    return locale === "ru" ? "сейчас" : "now";
  }

  return locale === "ru" ? `через ${seconds}с` : `in ${seconds}s`;
}

export function GenerationStatusPanel({
  job,
  locale,
  isRefreshing,
  queueRefreshRemainingSeconds,
  onRefresh,
}: {
  job: GenerationJobState | null;
  locale: Locale;
  isRefreshing: boolean;
  queueRefreshRemainingSeconds: number;
  onRefresh: () => void;
}) {
  const showQueueCard = job?.status === "pending";

  return (
    <>
      <GenerationStatusRail job={job} locale={locale} isPreparing={false} />

      {showQueueCard && job ? (
        <div className="mb-3 flex items-start justify-between gap-3 border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <div className="space-y-1">
            <p className="font-medium">
              {locale === "ru"
                ? `Очередь на генерацию: позиция ${job.queue_position ?? 1}`
                : `Generation queue: position ${job.queue_position ?? 1}`}
            </p>
            <p className="text-xs leading-5 text-amber-800">
              {locale === "ru"
                ? "Изображение генерируется асинхронно. Чат остаётся доступным, а позицию в очереди можно обновить отдельно."
                : "Image generation is asynchronous. The chat stays available, and the queue position can be refreshed separately."}
            </p>
          </div>
          <button
            type="button"
            onClick={onRefresh}
            disabled={isRefreshing || queueRefreshRemainingSeconds > 0}
            className="inline-flex items-center gap-2 border border-amber-300 bg-white px-3 py-2 text-xs font-medium uppercase tracking-[0.18em] text-amber-900 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:border-amber-200 disabled:bg-amber-100 disabled:text-amber-500"
          >
            <span>
              {queueRefreshRemainingSeconds > 0
                ? formatSecondsLabel(locale, queueRefreshRemainingSeconds)
                : locale === "ru"
                  ? "обновить"
                  : "refresh"}
            </span>
          </button>
        </div>
      ) : null}
    </>
  );
}
