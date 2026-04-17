"use client";

import Image from "next/image";

import { GenerationStyleExplanation } from "@/entities/generation-job/ui/GenerationStyleExplanation";
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
            ? "РќРµ СѓРґР°Р»РѕСЃСЊ СЃРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ РёР·РѕР±СЂР°Р¶РµРЅРёРµ."
            : "Could not generate the image.")}
      </div>
    );
  }

  if (!job?.result_url) {
    return null;
  }

  return (
    <div className="mt-3 w-full max-w-[320px] space-y-3">
      <a
        href={job.result_url}
        target="_blank"
        rel="noreferrer"
        className="block cursor-pointer overflow-hidden border border-slate-200 bg-white"
        title={locale === "ru" ? "РћС‚РєСЂС‹С‚СЊ РёР·РѕР±СЂР°Р¶РµРЅРёРµ" : "Open image"}
      >
        <Image
          src={job.result_url}
          alt={locale === "ru" ? "РЎРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Р№ flat lay" : "Generated flat lay"}
          width={1024}
          height={1024}
          className="h-auto w-full object-cover transition duration-200 hover:scale-[1.01]"
          unoptimized
        />
      </a>
      <GenerationStyleExplanation job={job} locale={locale} />
    </div>
  );
}
