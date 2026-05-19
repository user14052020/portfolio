"use client";

import { Select, Switch, Textarea, TextInput } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getSiteSettings, updateSiteSettings } from "@/shared/api/client";
import type { SiteMetaContent, SiteSettings } from "@/shared/api/types";
import { normalizeHomepageContent } from "@/shared/config/homepageContent";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";
import { buildSiteSettingsUpdatePayload } from "@/widgets/admin/model/siteSettingsPayload";

type SiteMetaTextField = keyof Omit<SiteMetaContent, "keywords" | "robots_index" | "robots_follow">;

export function SiteMetaManager() {
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
        setError(nextError instanceof Error ? nextError.message : "Failed to load meta tags");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  function updateMetaField(field: SiteMetaTextField, value: string) {
    setSettings((current) =>
      current
        ? {
            ...current,
            homepage_content: {
              ...current.homepage_content,
              site_meta: {
                ...current.homepage_content.site_meta,
                [field]: value,
              },
            },
          }
        : current,
    );
  }

  function updateMetaBoolean(field: "robots_index" | "robots_follow", value: boolean) {
    setSettings((current) =>
      current
        ? {
            ...current,
            homepage_content: {
              ...current.homepage_content,
              site_meta: {
                ...current.homepage_content.site_meta,
                [field]: value,
              },
            },
          }
        : current,
    );
  }

  function updateKeywords(value: string) {
    setSettings((current) =>
      current
        ? {
            ...current,
            homepage_content: {
              ...current.homepage_content,
              site_meta: {
                ...current.homepage_content.site_meta,
                keywords: value
                  .split(",")
                  .map((item) => item.trim())
                  .filter(Boolean),
              },
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
      setError(nextError instanceof Error ? nextError.message : "Failed to save meta tags");
    } finally {
      setIsSaving(false);
    }
  }

  if (!settings) {
    return (
      <SurfaceCard variant="elevated">
        <div className="space-y-3">
          <PillBadge tone={error ? "rose" : "subtle"}>{error ? "Meta error" : "Loading"}</PillBadge>
          <p className={error ? "text-sm text-rose-700" : "text-sm text-[var(--text-secondary)]"}>
            {error ?? "Loading site meta tags..."}
          </p>
        </div>
      </SurfaceCard>
    );
  }

  const meta = normalizeHomepageContent(settings.homepage_content).site_meta;

  return (
    <div className="space-y-7">
      <SectionHeader
        eyebrow="SEO"
        title="Site meta tags"
        description="Edit global title, description, Open Graph, Twitter and indexing directives from the admin panel."
        action={
          <SoftButton tone="dark" onClick={handleSave} disabled={isSaving || !tokens?.access_token}>
            {isSaving ? "Saving..." : "Save meta tags"}
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
          <MetaCardHeader
            eyebrow="Base"
            title="Title, description and canonical"
            description="These values drive browser title, search snippets and canonical URL."
          />
        }
      >
        <div className="grid gap-4 md:grid-cols-2">
          <TextInput
            label="Title RU"
            value={meta.title_ru}
            onChange={(event) => updateMetaField("title_ru", event.currentTarget.value)}
          />
          <TextInput
            label="Title EN"
            value={meta.title_en}
            onChange={(event) => updateMetaField("title_en", event.currentTarget.value)}
          />
          <Textarea
            label="Description RU"
            minRows={4}
            value={meta.description_ru}
            onChange={(event) => updateMetaField("description_ru", event.currentTarget.value)}
          />
          <Textarea
            label="Description EN"
            minRows={4}
            value={meta.description_en}
            onChange={(event) => updateMetaField("description_en", event.currentTarget.value)}
          />
          <TextInput
            label="Keywords"
            description="Comma-separated list"
            value={meta.keywords.join(", ")}
            onChange={(event) => updateKeywords(event.currentTarget.value)}
          />
          <TextInput
            label="Canonical URL"
            value={meta.canonical_url ?? ""}
            onChange={(event) => updateMetaField("canonical_url", event.currentTarget.value)}
          />
        </div>
      </SurfaceCard>

      <SurfaceCard
        variant="tinted"
        header={
          <MetaCardHeader
            eyebrow="Social"
            title="Open Graph and Twitter"
            description="Preview data used by messengers, social feeds and rich link embeds."
          />
        }
      >
        <div className="grid gap-4 md:grid-cols-2">
          <TextInput
            label="OG title RU"
            value={meta.og_title_ru}
            onChange={(event) => updateMetaField("og_title_ru", event.currentTarget.value)}
          />
          <TextInput
            label="OG title EN"
            value={meta.og_title_en}
            onChange={(event) => updateMetaField("og_title_en", event.currentTarget.value)}
          />
          <Textarea
            label="OG description RU"
            minRows={3}
            value={meta.og_description_ru}
            onChange={(event) => updateMetaField("og_description_ru", event.currentTarget.value)}
          />
          <Textarea
            label="OG description EN"
            minRows={3}
            value={meta.og_description_en}
            onChange={(event) => updateMetaField("og_description_en", event.currentTarget.value)}
          />
          <TextInput
            label="OG image URL"
            value={meta.og_image ?? ""}
            onChange={(event) => updateMetaField("og_image", event.currentTarget.value)}
          />
          <Select
            label="Twitter card"
            data={[
              { value: "summary_large_image", label: "summary_large_image" },
              { value: "summary", label: "summary" },
            ]}
            value={meta.twitter_card}
            onChange={(value) => updateMetaField("twitter_card", value ?? "summary_large_image")}
          />
        </div>
      </SurfaceCard>

      <SurfaceCard
        variant="soft"
        header={
          <MetaCardHeader
            eyebrow="Robots"
            title="Indexing and browser theme"
            description="Control robots directives and the browser chrome color."
          />
        }
      >
        <div className="grid gap-4 md:grid-cols-3">
          <TextInput
            label="Theme color"
            value={meta.theme_color}
            onChange={(event) => updateMetaField("theme_color", event.currentTarget.value)}
          />
          <Switch
            label="Allow indexing"
            checked={meta.robots_index}
            onChange={(event) => updateMetaBoolean("robots_index", event.currentTarget.checked)}
          />
          <Switch
            label="Allow following links"
            checked={meta.robots_follow}
            onChange={(event) => updateMetaBoolean("robots_follow", event.currentTarget.checked)}
          />
        </div>
      </SurfaceCard>
    </div>
  );
}

function MetaCardHeader({
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
