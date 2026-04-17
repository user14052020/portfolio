import Image from "next/image";
import { Loader } from "@mantine/core";

import { GenerationStyleExplanation } from "@/entities/generation-job/ui/GenerationStyleExplanation";
import type { GenerationJob, Locale } from "@/shared/api/types";

function getStatusLabel(locale: Locale, job: GenerationJob | null, isPreparing: boolean) {
  if (isPreparing && !job) {
    return locale === "ru" ? "РџРѕРґРіРѕС‚Р°РІР»РёРІР°СЋ" : "Preparing";
  }

  switch (job?.status) {
    case "pending":
      return locale === "ru" ? "РћР¶РёРґР°РЅРёРµ" : "Pending";
    case "queued":
      return locale === "ru" ? "Р’ РѕС‡РµСЂРµРґРё" : "Queued";
    case "running":
      return locale === "ru" ? "Р“РµРЅРµСЂРёСЂСѓСЋ" : "Generating";
    case "completed":
      return locale === "ru" ? "Р“РѕС‚РѕРІРѕ" : "Done";
    case "failed":
      return locale === "ru" ? "РћС€РёР±РєР°" : "Failed";
    default:
      return locale === "ru" ? "РџРѕРґРіРѕС‚Р°РІР»РёРІР°СЋ" : "Preparing";
  }
}

function getProgress(job: GenerationJob | null, isPreparing: boolean) {
  if (job) {
    return Math.min(100, Math.max(0, job.progress));
  }
  return isPreparing ? 8 : 0;
}

export function GenerationResultCard({
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
      ? "РћС‚РїСЂР°РІР»СЏСЋ Р·Р°РїСЂРѕСЃ РЅР° СЃРµСЂРІРµСЂ Рё РїРѕРґРіРѕС‚Р°РІР»РёРІР°СЋ РіРµРЅРµСЂР°С†РёСЋ РѕР±СЂР°Р·Р°."
      : "Sending the request to the server and preparing the outfit generation."
    : locale === "ru"
      ? "РР·РѕР±СЂР°Р¶РµРЅРёРµ РїРѕСЏРІРёС‚СЃСЏ Р·РґРµСЃСЊ, РєР°Рє С‚РѕР»СЊРєРѕ backend РїРѕР»СѓС‡РёС‚ РїРµСЂРІС‹Р№ СЂРµР·СѓР»СЊС‚Р°С‚ РѕС‚ РіРµРЅРµСЂР°С‚РѕСЂР°."
      : "The image will appear here as soon as the backend receives the first result from the generator.";

  return (
    <div className="max-w-[620px] space-y-2">
      <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">{assistantLabel}</p>
      <div className="w-full max-w-[620px] border border-slate-200 bg-slate-50 p-3">
        <div className="mb-3 flex items-center justify-between gap-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-slate-500">
            {locale === "ru" ? "Р“РµРЅРµСЂР°С†РёСЏ РѕР±СЂР°Р·Р°" : "Outfit generation"}
          </p>
          <p className="text-xs text-slate-500">{statusLabel}</p>
        </div>

        {job?.result_url ? (
          <div className="overflow-hidden border border-slate-200 bg-white">
            <Image
              src={job.result_url}
              alt={locale === "ru" ? "РЎРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Р№ РѕР±СЂР°Р·" : "Generated outfit"}
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

        {job?.result_url ? (
          <div className="mt-3">
            <GenerationStyleExplanation job={job} locale={locale} />
          </div>
        ) : null}

        <div className="mt-3 h-1.5 overflow-hidden bg-slate-200">
          <div
            className="h-full bg-gradient-to-r from-[#d0a46d] to-[#8fae98] transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="mt-3 space-y-2">
          {recommendation ? (
            <p className="text-sm leading-6 text-slate-600">
              {locale === "ru" ? "Р РµРєРѕРјРµРЅРґР°С†РёСЏ:" : "Recommendation:"} {recommendation}
            </p>
          ) : null}
          {job?.error_message ? <p className="text-sm leading-6 text-rose-600">{job.error_message}</p> : null}
        </div>
      </div>
    </div>
  );
}
