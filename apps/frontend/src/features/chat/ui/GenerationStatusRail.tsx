"use client";

import type { GenerationJob, Locale } from "@/shared/api/types";

function getProgress(job: GenerationJob | null, isPreparing: boolean) {
  if (isPreparing && !job) {
    return 10;
  }

  if (!job) {
    return 0;
  }

  if (job.status === "pending") {
    if (job.queue_position && job.queue_total && job.queue_total > 0) {
      const completion = (job.queue_total - job.queue_position + 1) / job.queue_total;
      return Math.max(8, Math.min(28, Math.round(completion * 28)));
    }
    return 8;
  }

  if (job.status === "queued") {
    return Math.max(job.progress || 0, 24);
  }

  if (job.status === "running") {
    return Math.max(job.progress || 0, 38);
  }

  return 100;
}

function getLabels(job: GenerationJob | null, locale: Locale, isPreparing: boolean) {
  if (isPreparing && !job) {
    return {
      title: locale === "ru" ? "Подготовка генерации" : "Preparing generation",
      detail:
        locale === "ru"
          ? "Отправляю запрос на backend и собираю задачу."
          : "Sending the request to the backend and assembling the job.",
    };
  }

  if (!job) {
    return null;
  }

  if (job.status === "pending") {
    return {
      title:
        locale === "ru"
          ? `Очередь на генерацию${job.queue_position ? `: позиция ${job.queue_position}` : ""}`
          : `Generation queue${job.queue_position ? `: position ${job.queue_position}` : ""}`,
      detail:
        locale === "ru"
          ? "Задача ждёт свободный слот генерации."
          : "The job is waiting for a free generation slot.",
    };
  }

  if (job.status === "queued") {
    return {
      title: locale === "ru" ? "Задача отправлена в ComfyUI" : "Job submitted to ComfyUI",
      detail:
        locale === "ru"
          ? "Генератор принял задачу и готовит выполнение."
          : "The generator accepted the job and is preparing execution.",
    };
  }

  if (job.status === "running") {
    return {
      title: locale === "ru" ? "Генерация идёт" : "Generation in progress",
      detail:
        locale === "ru"
          ? "Изображение появится в чате, как только будет готов результат."
          : "The image will appear in the chat as soon as the result is ready.",
    };
  }

  return null;
}

export function GenerationStatusRail({
  job,
  locale,
  isPreparing,
}: {
  job: GenerationJob | null;
  locale: Locale;
  isPreparing: boolean;
}) {
  const labels = getLabels(job, locale, isPreparing);
  if (!labels) {
    return null;
  }

  return (
    <div className="mb-3 border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-800">{labels.title}</p>
        <span className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
          {Math.round(getProgress(job, isPreparing))}%
        </span>
      </div>
      <div className="h-1.5 overflow-hidden bg-slate-200">
        <div
          className="h-full bg-gradient-to-r from-[#d0a46d] to-[#8fae98] transition-all duration-500"
          style={{ width: `${getProgress(job, isPreparing)}%` }}
        />
      </div>
      <p className="mt-2 text-xs leading-5 text-slate-600">{labels.detail}</p>
    </div>
  );
}
