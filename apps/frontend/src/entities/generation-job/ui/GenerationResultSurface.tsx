import Image from "next/image";

import { GenerationStyleExplanation } from "@/entities/generation-job/ui/GenerationStyleExplanation";
import type { GenerationJob, Locale } from "@/shared/api/types";

export function GenerationResultSurface({
  job,
  locale,
  assistantLabel,
  isPreparing,
}: {
  job: GenerationJob | null;
  locale: Locale;
  assistantLabel: string;
  isPreparing: boolean;
}) {
  if ((!job || !job.result_url) && !isPreparing) {
    return null;
  }

  if (job?.status === "failed" || job?.status === "cancelled") {
    return (
      <div className="max-w-[620px] space-y-2">
        <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--text-muted)]">{assistantLabel}</p>
        <div className="w-full max-w-[620px] rounded-[24px] rounded-tl-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-700 shadow-sm">
          {job.error_message ||
            (locale === "ru" ? "Не удалось сгенерировать изображение." : "Could not generate the image.")}
        </div>
      </div>
    );
  }

  if (!job?.result_url) {
    return null;
  }

  const recommendation = locale === "ru" ? job.recommendation_ru : job.recommendation_en;

  return (
    <div className="max-w-[620px] space-y-2">
      <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--text-muted)]">{assistantLabel}</p>
      <div className="w-full max-w-[620px] rounded-[28px] border border-[var(--border-soft)] bg-white/95 p-3 shadow-[var(--shadow-soft-md)]">
        <div className="overflow-hidden rounded-[24px] border border-[var(--border-soft)] bg-white shadow-[var(--shadow-soft-sm)]">
          <Image
            src={job.result_url}
            alt={locale === "ru" ? "Сгенерированный образ" : "Generated outfit"}
            width={1024}
            height={1024}
            className="h-auto w-full object-cover"
            unoptimized
          />
        </div>

        <div className="mt-3">
          <GenerationStyleExplanation job={job} locale={locale} />
        </div>

        {recommendation ? (
          <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
            {locale === "ru" ? "Рекомендация:" : "Recommendation:"} {recommendation}
          </p>
        ) : null}

        <a
          href={job.result_url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex rounded-[var(--radius-pill)] border border-[var(--border-soft)] bg-white/80 px-3 py-1.5 text-sm font-medium text-[var(--text-primary)] transition hover:border-[var(--border-strong)] hover:bg-white"
        >
          {locale === "ru" ? "Открыть изображение" : "Open image"}
        </a>
      </div>
    </div>
  );
}
