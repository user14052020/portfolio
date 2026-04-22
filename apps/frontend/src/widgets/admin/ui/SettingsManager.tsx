"use client";

import { Textarea, TextInput } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getSiteSettings, updateSiteSettings } from "@/shared/api/client";
import type { SiteSettings } from "@/shared/api/types";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";
import { StyleIngestionSettingsManager } from "@/widgets/admin/ui/StyleIngestionSettingsManager";
import { StylistRuntimeSettingsManager } from "@/widgets/admin/ui/StylistRuntimeSettingsManager";

type SiteSettingsTextField = keyof Pick<
  SiteSettings,
  | "brand_name"
  | "contact_email"
  | "assistant_name_ru"
  | "assistant_name_en"
  | "hero_title_ru"
  | "hero_title_en"
  | "hero_subtitle_ru"
  | "hero_subtitle_en"
  | "about_text_ru"
  | "about_text_en"
>;

export function SettingsManager() {
  const { tokens } = useAdminAuth();
  const [settings, setSettings] = useState<SiteSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;

    getSiteSettings()
      .then((nextSettings) => {
        if (cancelled) {
          return;
        }
        setSettings(nextSettings);
        setError(null);
      })
      .catch((nextError) => {
        if (cancelled) {
          return;
        }
        setError(nextError instanceof Error ? nextError.message : "Failed to load site settings");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  function updateTextField(field: SiteSettingsTextField, value: string) {
    setSettings((current) => (current ? { ...current, [field]: value } : current));
  }

  function updateSkills(value: string) {
    setSettings((current) =>
      current
        ? {
            ...current,
            skills: value
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
          }
        : current
    );
  }

  async function handleSave() {
    if (!tokens?.access_token || !settings) {
      return;
    }

    setIsSaving(true);
    try {
      const updated = await updateSiteSettings(
        {
          brand_name: settings.brand_name,
          contact_email: settings.contact_email,
          contact_phone: settings.contact_phone,
          assistant_name_ru: settings.assistant_name_ru,
          assistant_name_en: settings.assistant_name_en,
          hero_title_ru: settings.hero_title_ru,
          hero_title_en: settings.hero_title_en,
          hero_subtitle_ru: settings.hero_subtitle_ru,
          hero_subtitle_en: settings.hero_subtitle_en,
          about_title_ru: settings.about_title_ru,
          about_title_en: settings.about_title_en,
          about_text_ru: settings.about_text_ru,
          about_text_en: settings.about_text_en,
          socials: settings.socials,
          skills: settings.skills,
        },
        tokens.access_token
      );
      setSettings(updated);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to save site settings");
    } finally {
      setIsSaving(false);
    }
  }

  if (!settings) {
    return (
      <SurfaceCard variant="elevated">
        <div className="space-y-3">
          <PillBadge tone={error ? "rose" : "subtle"}>{error ? "Settings error" : "Loading"}</PillBadge>
          <p className={error ? "text-sm text-rose-700" : "text-sm text-[var(--text-secondary)]"}>
            {error ?? "Loading site settings..."}
          </p>
        </div>
      </SurfaceCard>
    );
  }

  return (
    <div className="space-y-7">
      <SectionHeader
        eyebrow="Admin settings"
        title="Runtime and content cockpit"
        description="Manage homepage copy, assistant identity, stylist runtime limits and parser timing from one operational surface."
        action={
          <SoftButton tone="dark" onClick={handleSave} disabled={isSaving || !tokens?.access_token}>
            {isSaving ? "Saving..." : "Save site settings"}
          </SoftButton>
        }
      />

      {error ? (
        <SurfaceCard variant="soft" padding="sm" className="border-rose-200 bg-rose-50/80">
          <p className="text-sm text-rose-700">{error}</p>
        </SurfaceCard>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <SurfaceCard
          variant="elevated"
          header={
            <SettingsCardHeader
              eyebrow="Identity"
              title="Brand and assistant"
              description="The public voice of the product and AI stylist."
            />
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            <TextInput
              label="Brand name"
              value={settings.brand_name}
              onChange={(event) => updateTextField("brand_name", event.currentTarget.value)}
            />
            <TextInput
              label="Contact email"
              value={settings.contact_email}
              onChange={(event) => updateTextField("contact_email", event.currentTarget.value)}
            />
            <TextInput
              label="Assistant name RU"
              value={settings.assistant_name_ru}
              onChange={(event) => updateTextField("assistant_name_ru", event.currentTarget.value)}
            />
            <TextInput
              label="Assistant name EN"
              value={settings.assistant_name_en}
              onChange={(event) => updateTextField("assistant_name_en", event.currentTarget.value)}
            />
          </div>
        </SurfaceCard>

        <SurfaceCard
          variant="tinted"
          header={
            <SettingsCardHeader
              eyebrow="Homepage hero"
              title="Landing page copy"
              description="Primary headline and assistant-led promise on the homepage."
            />
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            <TextInput
              label="Hero title RU"
              value={settings.hero_title_ru}
              onChange={(event) => updateTextField("hero_title_ru", event.currentTarget.value)}
            />
            <TextInput
              label="Hero title EN"
              value={settings.hero_title_en}
              onChange={(event) => updateTextField("hero_title_en", event.currentTarget.value)}
            />
            <Textarea
              label="Hero subtitle RU"
              minRows={4}
              value={settings.hero_subtitle_ru}
              onChange={(event) => updateTextField("hero_subtitle_ru", event.currentTarget.value)}
            />
            <Textarea
              label="Hero subtitle EN"
              minRows={4}
              value={settings.hero_subtitle_en}
              onChange={(event) => updateTextField("hero_subtitle_en", event.currentTarget.value)}
            />
          </div>
        </SurfaceCard>
      </div>

      <SurfaceCard
        variant="soft"
        header={
          <SettingsCardHeader
            eyebrow="Profile"
            title="About and skills"
            description="Supporting copy for the portfolio sections below the assistant hero."
          />
        }
      >
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr_0.9fr]">
          <Textarea
            label="About text RU"
            minRows={5}
            value={settings.about_text_ru}
            onChange={(event) => updateTextField("about_text_ru", event.currentTarget.value)}
          />
          <Textarea
            label="About text EN"
            minRows={5}
            value={settings.about_text_en}
            onChange={(event) => updateTextField("about_text_en", event.currentTarget.value)}
          />
          <div className="space-y-3">
            <TextInput
              label="Skills"
              description="Comma-separated list"
              value={settings.skills.join(", ")}
              onChange={(event) => updateSkills(event.currentTarget.value)}
            />
            <div className="flex flex-wrap gap-2">
              {settings.skills.slice(0, 8).map((skill) => (
                <PillBadge key={skill} tone="neutral" size="sm">
                  {skill}
                </PillBadge>
              ))}
            </div>
          </div>
        </div>
      </SurfaceCard>

      <StylistRuntimeSettingsManager />

      <StyleIngestionSettingsManager />
    </div>
  );
}

function SettingsCardHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--text-muted)]">{eyebrow}</p>
      <h2 className="font-display text-2xl text-[var(--text-primary)]">{title}</h2>
      <p className="text-sm text-[var(--text-secondary)]">{description}</p>
    </div>
  );
}
