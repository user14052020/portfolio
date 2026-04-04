"use client";

import type { SiteSettings } from "@/shared/api/types";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function AboutSection({
  settings,
  locale
}: {
  settings: SiteSettings;
  locale: "ru" | "en";
}) {
  return (
    <WindowFrame>
      <div className="space-y-5">
        <p className="max-w-4xl text-base leading-8 text-slate-600">{pickLocalized(settings, "about_text", locale)}</p>
        <div className="flex flex-wrap gap-2">
          {settings.skills.map((skill) => (
            <span
              key={skill}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700"
            >
              {skill}
            </span>
          ))}
        </div>
      </div>
    </WindowFrame>
  );
}
