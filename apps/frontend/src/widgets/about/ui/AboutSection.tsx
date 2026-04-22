"use client";

import type { SiteSettings } from "@/shared/api/types";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function AboutSection({
  settings,
  locale
}: {
  settings: SiteSettings;
  locale: "ru" | "en";
}) {
  return (
    <WindowFrame variant="elevated" decorativeTone="lilac" bodyClassName="p-6 md:p-9">
      <div className="grid gap-8 lg:grid-cols-[0.72fr_1fr] lg:items-start">
        <SectionHeader
          eyebrow={locale === "ru" ? "Контекст" : "Context"}
          title={pickLocalized(settings, "about_title", locale)}
          description={locale === "ru" ? "Кто собирает эту систему и почему ей можно доверять." : "Who is shaping this system and why it is built with care."}
        />
        <div className="space-y-6 rounded-[28px] bg-white/60 p-5 md:p-6">
          <p className="text-base leading-8 text-[var(--text-secondary)]">{pickLocalized(settings, "about_text", locale)}</p>
          <div className="flex flex-wrap gap-2">
            {settings.skills.map((skill) => (
              <PillBadge key={skill} tone="neutral" size="sm" className="normal-case tracking-normal">
                {skill}
              </PillBadge>
            ))}
          </div>
        </div>
      </div>
    </WindowFrame>
  );
}
