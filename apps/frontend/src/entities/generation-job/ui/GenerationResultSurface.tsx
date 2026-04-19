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
        <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">{assistantLabel}</p>
        <div className="w-full max-w-[620px] rounded-[24px] rounded-tl-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-700 shadow-sm">
          {job.error_message ||
            (locale === "ru" ? "РќРµ СѓРґР°Р»РѕСЃСЊ СЃРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ РёР·РѕР±СЂР°Р¶РµРЅРёРµ." : "Could not generate the image.")}
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
      <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">{assistantLabel}</p>
      <div className="w-full max-w-[620px] rounded-[28px] border border-slate-200 bg-white/95 p-3 shadow-[0_18px_42px_rgba(15,23,42,0.08)]">
        <div className="overflow-hidden rounded-[22px] border border-slate-200 bg-white">
          <Image
            src={job.result_url}
            alt={locale === "ru" ? "РЎРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Р№ РѕР±СЂР°Р·" : "Generated outfit"}
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
          <p className="mt-3 text-sm leading-6 text-slate-600">
            {locale === "ru" ? "Р РµРєРѕРјРµРЅРґР°С†РёСЏ:" : "Recommendation:"} {recommendation}
          </p>
        ) : null}

        <a
          href={job.result_url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex rounded-full border border-slate-200 bg-white/80 px-3 py-1.5 text-sm font-medium text-slate-900 transition hover:border-slate-300 hover:bg-white"
        >
          {locale === "ru" ? "РћС‚РєСЂС‹С‚СЊ РёР·РѕР±СЂР°Р¶РµРЅРёРµ" : "Open image"}
        </a>
      </div>
    </div>
  );
}
