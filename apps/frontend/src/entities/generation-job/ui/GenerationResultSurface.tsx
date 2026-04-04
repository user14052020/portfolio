import Image from "next/image";
import { Loader } from "@mantine/core";

import type { GenerationJob, Locale } from "@/shared/api/types";

function getStatusLabel(locale: Locale, job: GenerationJob | null, isPreparing: boolean) {
  if (isPreparing && !job) {
    return locale === "ru" ? "Подготавливаю" : "Preparing";
  }

  switch (job?.status) {
    case "pending":
      return locale === "ru" ? "Ожидание" : "Pending";
    case "queued":
      return locale === "ru" ? "В очереди" : "Queued";
    case "running":
      return locale === "ru" ? "Генерирую" : "Generating";
    case "completed":
      return locale === "ru" ? "Готово" : "Done";
    case "failed":
      return locale === "ru" ? "Ошибка" : "Failed";
    default:
      return locale === "ru" ? "Подготавливаю" : "Preparing";
  }
}

function getProgress(job: GenerationJob | null, isPreparing: boolean) {
  if (job) {
    return Math.min(100, Math.max(0, job.progress));
  }
  return isPreparing ? 8 : 0;
}

export function GenerationResultSurface({
  job,
  locale,
  assistantLabel,
  isPreparing
}: {
  job: GenerationJob | null;
  locale: Locale;
  assistantLabel: string;
  isPreparing: boolean;
}) {
  if (!job && !isPreparing) {
    return null;
  }

  const statusLabel = getStatusLabel(locale, job, isPreparing);
  const progress = getProgress(job, isPreparing);
  const recommendation = job ? (locale === "ru" ? job.recommendation_ru : job.recommendation_en) : null;
  const waitingText = isPreparing
    ? locale === "ru"
      ? "Отправляю запрос на сервер и подготавливаю генерацию образа."
      : "Sending the request to the server and preparing the outfit generation."
    : locale === "ru"
      ? "Изображение появится здесь, как только backend получит первый результат от генератора."
      : "The image will appear here as soon as the backend receives the first result from the generator.";

  return (
    <div className="max-w-[620px] space-y-2">
      <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">{assistantLabel}</p>
      <div className="w-full max-w-[620px] border border-slate-200 bg-slate-50 p-3">
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-slate-500">
            {locale === "ru" ? "Генерация образа" : "Outfit generation"}
          </p>
          <p className="text-xs text-slate-500">{statusLabel}</p>
        </div>

        {job ? (
          <div className="mb-3 flex flex-wrap gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-500">
            <span className="border border-slate-200 bg-white px-2 py-1">{job.provider}</span>
            <span className="border border-slate-200 bg-white px-2 py-1">
              {locale === "ru" ? "Задача" : "Job"}: {job.public_id}
            </span>
          </div>
        ) : null}

        {job?.result_url ? (
          <div className="overflow-hidden border border-slate-200 bg-white">
            <Image
              src={job.result_url}
              alt={locale === "ru" ? "Сгенерированный образ" : "Generated outfit"}
              width={1024}
              height={1024}
              className="h-auto w-full object-cover"
              unoptimized
            />
          </div>
        ) : (
          <div className="relative flex aspect-square items-center justify-center overflow-hidden border border-slate-200 bg-[radial-gradient(circle_at_top,_rgba(208,164,109,0.22),_transparent_45%),linear-gradient(135deg,_#f8fafc,_#eef2f7)]">
            <div className="absolute inset-0 animate-pulse bg-[linear-gradient(135deg,rgba(255,255,255,0.1),rgba(255,255,255,0.45),rgba(255,255,255,0.08))]" />
            <div className="relative z-10 flex flex-col items-center gap-3 px-6 text-center">
              <Loader size="sm" color="dark" />
              <p className="max-w-[280px] text-sm leading-6 text-slate-600">{waitingText}</p>
            </div>
          </div>
        )}

        <div className="mt-3 h-1.5 overflow-hidden bg-slate-200">
          <div
            className="h-full bg-gradient-to-r from-[#d0a46d] to-[#8fae98] transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="mt-3 space-y-2">
          {recommendation ? (
            <p className="text-sm leading-6 text-slate-600">
              {locale === "ru" ? "Рекомендация:" : "Recommendation:"} {recommendation}
            </p>
          ) : null}
          {job?.error_message ? <p className="text-sm leading-6 text-rose-600">{job.error_message}</p> : null}
          {job?.result_url ? (
            <a
              href={job.result_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex text-sm font-medium text-slate-900 underline decoration-slate-300 underline-offset-4 transition hover:decoration-slate-600"
            >
              {locale === "ru" ? "Открыть изображение" : "Open image"}
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}
