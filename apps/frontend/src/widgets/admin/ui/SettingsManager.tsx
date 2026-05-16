"use client";

import { Select, Switch, Textarea, TextInput } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getSiteSettings, updateSiteSettings } from "@/shared/api/client";
import type { HomepageContent, SiteSettings } from "@/shared/api/types";
import { normalizeHomepageContent, showcaseVisualOptions } from "@/shared/config/homepageContent";
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
  | "about_title_ru"
  | "about_title_en"
  | "about_text_ru"
  | "about_text_en"
>;

type HomepageContentTextField = keyof Omit<HomepageContent, "hero_eyebrow_items" | "hero_preview">;

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
        setSettings({
          ...nextSettings,
          homepage_content: normalizeHomepageContent(nextSettings.homepage_content),
        });
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

  function updateSocial(field: string, value: string) {
    setSettings((current) =>
      current
        ? {
            ...current,
            socials: {
              ...current.socials,
              [field]: value,
            },
          }
        : current
    );
  }

  function updateHomepageEyebrowItems(value: string) {
    setSettings((current) =>
      current
        ? {
            ...current,
            homepage_content: {
              ...current.homepage_content,
              hero_eyebrow_items: value
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean),
            },
          }
        : current
    );
  }

  function updateHomepageField(field: HomepageContentTextField, value: string) {
    setSettings((current) =>
      current
        ? {
            ...current,
            homepage_content: {
              ...current.homepage_content,
              [field]: value,
            },
          }
        : current
    );
  }

  function updateHeroPreview(field: "visual_variant" | "video_duration", value: string) {
    setSettings((current) =>
      current
        ? {
            ...current,
            homepage_content: {
              ...current.homepage_content,
              hero_preview: {
                ...current.homepage_content.hero_preview,
                [field]: value,
              },
            },
          }
        : current
    );
  }

  function updateChatEnabled(value: boolean) {
    setSettings((current) => (current ? { ...current, chat_bot_enabled: value } : current));
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
          homepage_content: normalizeHomepageContent(settings.homepage_content),
          chat_bot_enabled: settings.chat_bot_enabled,
        },
        tokens.access_token
      );
      setSettings({
        ...updated,
        homepage_content: normalizeHomepageContent(updated.homepage_content),
      });
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
              label="Brand name RU"
              value={settings.homepage_content.brand_name_ru}
              onChange={(event) => updateHomepageField("brand_name_ru", event.currentTarget.value)}
            />
            <TextInput
              label="Brand name EN"
              value={settings.homepage_content.brand_name_en}
              onChange={(event) => updateHomepageField("brand_name_en", event.currentTarget.value)}
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
            <TextInput
              label="Telegram URL"
              value={settings.socials.telegram ?? ""}
              onChange={(event) => updateSocial("telegram", event.currentTarget.value)}
            />
            <TextInput
              label="GitHub URL"
              value={settings.socials.github ?? ""}
              onChange={(event) => updateSocial("github", event.currentTarget.value)}
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
        variant="elevated"
        header={
          <SettingsCardHeader
            eyebrow="Homepage showcase"
            title="Hero, contact CTA and chatbot"
            description="Editable content for the new portfolio layout and the paused chatbot block."
          />
        }
      >
        <div className="space-y-5">
          <div className="grid gap-4 lg:grid-cols-[0.85fr_0.75fr_0.75fr]">
            <TextInput
              label="Hero eyebrow items"
              description="Comma-separated list"
              value={settings.homepage_content.hero_eyebrow_items.join(", ")}
              onChange={(event) => updateHomepageEyebrowItems(event.currentTarget.value)}
            />
            <Select
              label="Hero preview visual"
              data={showcaseVisualOptions}
              value={settings.homepage_content.hero_preview.visual_variant}
              onChange={(value) => updateHeroPreview("visual_variant", value ?? "dashboard-dark")}
            />
            <TextInput
              label="Hero preview duration"
              value={settings.homepage_content.hero_preview.video_duration}
              onChange={(event) => updateHeroPreview("video_duration", event.currentTarget.value)}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <TextInput
              label="Technologies label RU"
              value={settings.homepage_content.technologies_label_ru}
              onChange={(event) => updateHomepageField("technologies_label_ru", event.currentTarget.value)}
            />
            <TextInput
              label="Technologies label EN"
              value={settings.homepage_content.technologies_label_en}
              onChange={(event) => updateHomepageField("technologies_label_en", event.currentTarget.value)}
            />
            <TextInput
              label="Project stack label RU"
              value={settings.homepage_content.project_stack_label_ru}
              onChange={(event) => updateHomepageField("project_stack_label_ru", event.currentTarget.value)}
            />
            <TextInput
              label="Project stack label EN"
              value={settings.homepage_content.project_stack_label_en}
              onChange={(event) => updateHomepageField("project_stack_label_en", event.currentTarget.value)}
            />
            <TextInput
              label="Header CTA RU"
              value={settings.homepage_content.header_cta_label_ru}
              onChange={(event) => updateHomepageField("header_cta_label_ru", event.currentTarget.value)}
            />
            <TextInput
              label="Header CTA EN"
              value={settings.homepage_content.header_cta_label_en}
              onChange={(event) => updateHomepageField("header_cta_label_en", event.currentTarget.value)}
            />
            <Textarea
              label="Contact title RU"
              minRows={3}
              value={settings.homepage_content.contact_title_ru}
              onChange={(event) => updateHomepageField("contact_title_ru", event.currentTarget.value)}
            />
            <Textarea
              label="Contact title EN"
              minRows={3}
              value={settings.homepage_content.contact_title_en}
              onChange={(event) => updateHomepageField("contact_title_en", event.currentTarget.value)}
            />
            <Textarea
              label="Contact description RU"
              minRows={3}
              value={settings.homepage_content.contact_description_ru}
              onChange={(event) => updateHomepageField("contact_description_ru", event.currentTarget.value)}
            />
            <Textarea
              label="Contact description EN"
              minRows={3}
              value={settings.homepage_content.contact_description_en}
              onChange={(event) => updateHomepageField("contact_description_en", event.currentTarget.value)}
            />
            <TextInput
              label="Telegram button RU"
              value={settings.homepage_content.telegram_label_ru}
              onChange={(event) => updateHomepageField("telegram_label_ru", event.currentTarget.value)}
            />
            <TextInput
              label="Telegram button EN"
              value={settings.homepage_content.telegram_label_en}
              onChange={(event) => updateHomepageField("telegram_label_en", event.currentTarget.value)}
            />
            <TextInput
              label="Email button RU"
              value={settings.homepage_content.email_label_ru}
              onChange={(event) => updateHomepageField("email_label_ru", event.currentTarget.value)}
            />
            <TextInput
              label="Email button EN"
              value={settings.homepage_content.email_label_en}
              onChange={(event) => updateHomepageField("email_label_en", event.currentTarget.value)}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-[0.5fr_1fr_1fr]">
            <Switch
              label="Chatbot enabled"
              description="Shows the chatbot block at the end of the homepage."
              checked={settings.chat_bot_enabled}
              onChange={(event) => updateChatEnabled(event.currentTarget.checked)}
            />
            <Textarea
              label="Chat section title RU"
              minRows={2}
              value={settings.homepage_content.chat_section_title_ru}
              onChange={(event) => updateHomepageField("chat_section_title_ru", event.currentTarget.value)}
            />
            <Textarea
              label="Chat section title EN"
              minRows={2}
              value={settings.homepage_content.chat_section_title_en}
              onChange={(event) => updateHomepageField("chat_section_title_en", event.currentTarget.value)}
            />
            <div className="lg:col-start-2">
              <Textarea
                label="Chat section description RU"
                minRows={3}
                value={settings.homepage_content.chat_section_description_ru}
                onChange={(event) => updateHomepageField("chat_section_description_ru", event.currentTarget.value)}
              />
            </div>
            <Textarea
              label="Chat section description EN"
              minRows={3}
              value={settings.homepage_content.chat_section_description_en}
              onChange={(event) => updateHomepageField("chat_section_description_en", event.currentTarget.value)}
            />
          </div>
        </div>
      </SurfaceCard>

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
          <TextInput
            label="About title RU"
            value={settings.about_title_ru}
            onChange={(event) => updateTextField("about_title_ru", event.currentTarget.value)}
          />
          <TextInput
            label="About title EN"
            value={settings.about_title_en}
            onChange={(event) => updateTextField("about_title_en", event.currentTarget.value)}
          />
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
