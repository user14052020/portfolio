"use client";

import { TextInput } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getSiteSettings, updateSiteSettings } from "@/shared/api/client";
import type { SiteSettings } from "@/shared/api/types";
import { normalizeHomepageContent } from "@/shared/config/homepageContent";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";
import { buildSiteSettingsUpdatePayload } from "@/widgets/admin/model/siteSettingsPayload";

type GeneralSettingsTextField = keyof Pick<
  SiteSettings,
  "brand_name" | "contact_email" | "contact_phone" | "assistant_name_ru" | "assistant_name_en"
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

  function updateTextField(field: GeneralSettingsTextField, value: string) {
    setSettings((current) => (current ? { ...current, [field]: value } : current));
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
        : current,
    );
  }

  async function handleSave() {
    if (!tokens?.access_token || !settings) {
      return;
    }

    setIsSaving(true);
    try {
      const updated = await updateSiteSettings(buildSiteSettingsUpdatePayload(settings), tokens.access_token);
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
        title="General site settings"
        description="Base identity, contacts and social links. Homepage copy, meta tags and runtime controls live on dedicated pages."
        action={
          <SoftButton tone="dark" onClick={handleSave} disabled={isSaving || !tokens?.access_token}>
            {isSaving ? "Saving..." : "Save settings"}
          </SoftButton>
        }
      />

      {error ? (
        <SurfaceCard variant="soft" padding="sm" className="border-rose-200 bg-rose-50/80">
          <p className="text-sm text-rose-700">{error}</p>
        </SurfaceCard>
      ) : null}

      <SurfaceCard
        variant="elevated"
        header={
          <SettingsCardHeader
            eyebrow="Identity"
            title="Brand, assistant and contacts"
            description="Global contact data used by forms, mail links and assistant surfaces."
          />
        }
      >
        <div className="grid gap-4 md:grid-cols-2">
          <TextInput
            label="Default brand name"
            description="Fallback for places without a localized brand name."
            value={settings.brand_name}
            onChange={(event) => updateTextField("brand_name", event.currentTarget.value)}
          />
          <TextInput
            label="Contact email"
            value={settings.contact_email}
            onChange={(event) => updateTextField("contact_email", event.currentTarget.value)}
          />
          <TextInput
            label="Contact phone"
            value={settings.contact_phone ?? ""}
            onChange={(event) => updateTextField("contact_phone", event.currentTarget.value)}
          />
          <TextInput
            label="Telegram URL"
            value={settings.socials.telegram ?? ""}
            onChange={(event) => updateSocial("telegram", event.currentTarget.value)}
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
            label="GitHub URL"
            value={settings.socials.github ?? ""}
            onChange={(event) => updateSocial("github", event.currentTarget.value)}
          />
          <TextInput
            label="LinkedIn URL"
            value={settings.socials.linkedin ?? ""}
            onChange={(event) => updateSocial("linkedin", event.currentTarget.value)}
          />
        </div>
      </SurfaceCard>
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
