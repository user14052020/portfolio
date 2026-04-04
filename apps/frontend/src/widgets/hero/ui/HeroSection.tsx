"use client";

import { Button } from "@mantine/core";

import type { SiteSettings } from "@/shared/api/types";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { ThreeScenePlaceholder } from "@/shared/ui/ThreeScenePlaceholder";

export function HeroSection({
  settings,
  onOpenContact
}: {
  settings: SiteSettings;
  onOpenContact: () => void;
}) {
  const { locale, t } = useI18n();

  return (
    <section className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
      <div className="space-y-6">
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-slate-500">
          {settings.contact_email}
        </p>
        <h1 className="max-w-4xl text-5xl font-semibold tracking-tight text-slate-950 md:text-7xl">
          {pickLocalized(settings, "hero_title", locale)}
        </h1>
        <p className="max-w-2xl text-lg leading-8 text-slate-600">
          {pickLocalized(settings, "hero_subtitle", locale)}
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Button radius="xl" size="lg" onClick={onOpenContact}>
            {t("writeMe")}
          </Button>
          <div className="flex flex-wrap gap-2">
            {settings.skills.map((skill) => (
              <span
                key={skill}
                className="rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-xs text-slate-600"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      </div>
      <ThreeScenePlaceholder title="Home ambient 3D block" sceneKey="home-sculpture" accent="#d0a46d" />
    </section>
  );
}

