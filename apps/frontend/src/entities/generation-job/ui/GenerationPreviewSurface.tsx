"use client";

import Image from "next/image";

import type { GenerationJob, Locale } from "@/shared/api/types";

export function GenerationPreviewSurface({
  job,
  locale,
  isPreparing,
}: {
  job: GenerationJob | null;
  locale: Locale;
  isPreparing: boolean;
}) {
  if ((!job || !job.result_url) && !isPreparing) {
    return null;
  }

  if (job?.status === "failed" || job?.status === "cancelled") {
    return (
      <div className="mt-3 max-w-[320px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-700">
        {job.error_message ||
          (locale === "ru"
            ? "Не удалось сгенерировать изображение."
            : "Could not generate the image.")}
      </div>
    );
  }

  if (!job?.result_url) {
    return null;
  }

  return (
    <a
      href={job.result_url}
      target="_blank"
      rel="noreferrer"
      className="mt-3 block w-full max-w-[320px] cursor-pointer overflow-hidden border border-slate-200 bg-white"
      title={locale === "ru" ? "Открыть изображение" : "Open image"}
    >
      <Image
        src={job.result_url}
        alt={locale === "ru" ? "Сгенерированный flat lay" : "Generated flat lay"}
        width={1024}
        height={1024}
        className="h-auto w-full object-cover transition duration-200 hover:scale-[1.01]"
        unoptimized
      />
    </a>
  );
}
