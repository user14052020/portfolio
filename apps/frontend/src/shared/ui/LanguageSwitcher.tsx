"use client";

import type { Locale } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n/I18nProvider";

const options: Array<{ label: string; value: Locale }> = [
  { label: "EN", value: "en" },
  { label: "RU", value: "ru" }
];

export function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();

  return (
    <div className="inline-flex border border-slate-200 bg-white">
      {options.map((option) => {
        const isActive = locale === option.value;

        return (
          <button
            key={option.value}
            type="button"
            onClick={() => setLocale(option.value)}
            className={
              isActive
                ? "min-w-[52px] border-r border-slate-200 bg-slate-900 px-3 py-2 text-xs font-medium tracking-[0.08em] text-white last:border-r-0"
                : "min-w-[52px] border-r border-slate-200 bg-white px-3 py-2 text-xs font-medium tracking-[0.08em] text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 last:border-r-0"
            }
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
