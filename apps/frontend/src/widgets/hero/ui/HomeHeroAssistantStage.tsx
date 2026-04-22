"use client";

import type { ReactNode } from "react";

import type { Locale, SiteSettings } from "@/shared/api/types";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";

const RU_ASSISTANT_STAGE = "AI stylist workspace";
const RU_PRIMARY_PROMISE = "Персональный стилист, который сначала думает текстом, а визуализацию запускает только когда это действительно нужно.";
const EN_PRIMARY_PROMISE = "A personal stylist that thinks in text first and only starts visualization when it actually helps.";

export function HomeHeroAssistantStage({
  settings,
  locale,
  onOpenContact,
  projectCount,
  postCount,
  children,
}: {
  settings: SiteSettings;
  locale: Locale;
  onOpenContact: () => void;
  projectCount: number;
  postCount: number;
  children: ReactNode;
}) {
  const assistantName = locale === "ru" ? settings.assistant_name_ru : settings.assistant_name_en;
  const skills = settings.skills.slice(0, 4);

  return (
    <section className="relative overflow-hidden rounded-[44px] border border-white/70 bg-[linear-gradient(135deg,rgba(255,255,255,0.92),rgba(247,245,240,0.78))] p-4 shadow-[var(--shadow-soft-xl)] md:p-6 lg:p-7">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_12%,rgba(208,164,109,0.24),transparent_26rem),radial-gradient(circle_at_88%_8%,rgba(239,237,255,0.82),transparent_30rem)]" />
      <div className="relative grid gap-6 lg:grid-cols-[0.78fr_1.22fr] lg:items-stretch">
        <div className="flex flex-col justify-between gap-8 rounded-[36px] border border-white/70 bg-white/70 p-6 backdrop-blur md:p-8">
          <div className="space-y-7">
            <div className="flex flex-wrap gap-2">
              <PillBadge tone="accent">{locale === "ru" ? RU_ASSISTANT_STAGE : "AI stylist workspace"}</PillBadge>
              <PillBadge tone="mint">{assistantName}</PillBadge>
            </div>

            <div className="space-y-5">
              <h1 className="font-display max-w-4xl text-5xl leading-[0.96] tracking-[-0.045em] text-[var(--text-primary)] md:text-7xl">
                {pickLocalized(settings, "hero_title", locale)}
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-[var(--text-secondary)]">
                {pickLocalized(settings, "hero_subtitle", locale)}
              </p>
              <p className="max-w-xl text-sm leading-7 text-[var(--text-muted)]">
                {locale === "ru" ? RU_PRIMARY_PROMISE : EN_PRIMARY_PROMISE}
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {skills.map((skill) => (
                <PillBadge key={skill} tone="subtle" size="sm">
                  {skill}
                </PillBadge>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <SurfaceCard variant="soft" padding="sm" className="rounded-[24px]">
                <p className="text-3xl font-semibold text-[var(--text-primary)]">{projectCount}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">
                  {locale === "ru" ? "проекты" : "projects"}
                </p>
              </SurfaceCard>
              <SurfaceCard variant="soft" padding="sm" className="rounded-[24px]">
                <p className="text-3xl font-semibold text-[var(--text-primary)]">{postCount}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">
                  {locale === "ru" ? "заметки" : "notes"}
                </p>
              </SurfaceCard>
            </div>
            <SoftButton tone="dark" shape="surface" fullWidth onClick={onOpenContact}>
              {locale === "ru" ? "Связаться и обсудить задачу" : "Talk through a project"}
            </SoftButton>
          </div>
        </div>

        <div className="relative">
          <div className="absolute -inset-2 rounded-[40px] bg-[linear-gradient(135deg,rgba(20,20,22,0.09),rgba(208,164,109,0.16),rgba(255,255,255,0.32))]" />
          <div className="relative">{children}</div>
        </div>
      </div>
    </section>
  );
}
