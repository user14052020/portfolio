"use client";

import { FileInput, NumberInput, Select, Textarea, TextInput } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getSiteSettings, updateSiteSettings, uploadAsset } from "@/shared/api/client";
import type { HomepageContent, HomepagePreviewContent, SiteSettings } from "@/shared/api/types";
import { normalizeHomepageContent, showcaseVisualOptions } from "@/shared/config/homepageContent";
import { contactSocialLinks } from "@/shared/config/socialLinks";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";
import { buildSiteSettingsUpdatePayload } from "@/widgets/admin/model/siteSettingsPayload";

type HomepageTextField = keyof Omit<
  HomepageContent,
  | "hero_eyebrow_items"
  | "hero_eyebrow_items_ru"
  | "hero_eyebrow_items_en"
  | "hero_title_rotating_items_ru"
  | "hero_title_rotating_items_en"
  | "hero_title_rotating_interval_ms"
  | "hero_title_rotating_animation_ms"
  | "hero_preview"
  | "site_meta"
  | "chat_section_title_ru"
  | "chat_section_title_en"
  | "chat_section_description_ru"
  | "chat_section_description_en"
>;
type RootHomepageTextField = keyof Pick<
  SiteSettings,
  | "hero_title_ru"
  | "hero_title_en"
  | "hero_subtitle_ru"
  | "hero_subtitle_en"
  | "contact_email"
>;

type ListDrafts = {
  heroEyebrowRu: string;
  heroEyebrowEn: string;
  heroTitleRotatingRu: string;
  heroTitleRotatingEn: string;
  skills: string;
};

const emptyListDrafts: ListDrafts = {
  heroEyebrowRu: "",
  heroEyebrowEn: "",
  heroTitleRotatingRu: "",
  heroTitleRotatingEn: "",
  skills: "",
};

function parseCommaList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatCommaList(items: string[]) {
  return items.join(", ");
}

function buildListDrafts(settings: SiteSettings): ListDrafts {
  const content = normalizeHomepageContent(settings.homepage_content);

  return {
    heroEyebrowRu: formatCommaList(content.hero_eyebrow_items_ru),
    heroEyebrowEn: formatCommaList(content.hero_eyebrow_items_en),
    heroTitleRotatingRu: formatCommaList(content.hero_title_rotating_items_ru),
    heroTitleRotatingEn: formatCommaList(content.hero_title_rotating_items_en),
    skills: formatCommaList(settings.skills),
  };
}

function applyListDrafts(settings: SiteSettings, drafts: ListDrafts): SiteSettings {
  const heroEyebrowItemsRu = parseCommaList(drafts.heroEyebrowRu);
  const heroEyebrowItemsEn = parseCommaList(drafts.heroEyebrowEn);
  const heroTitleRotatingItemsRu = parseCommaList(drafts.heroTitleRotatingRu);
  const heroTitleRotatingItemsEn = parseCommaList(drafts.heroTitleRotatingEn);

  return {
    ...settings,
    skills: parseCommaList(drafts.skills),
    homepage_content: {
      ...normalizeHomepageContent(settings.homepage_content),
      hero_eyebrow_items: heroEyebrowItemsEn,
      hero_eyebrow_items_ru: heroEyebrowItemsRu,
      hero_eyebrow_items_en: heroEyebrowItemsEn,
      hero_title_rotating_items_ru: heroTitleRotatingItemsRu,
      hero_title_rotating_items_en: heroTitleRotatingItemsEn,
    },
  };
}

export function HomepageContentManager() {
  const { tokens } = useAdminAuth();
  const [settings, setSettings] = useState<SiteSettings | null>(null);
  const [listDrafts, setListDrafts] = useState<ListDrafts>(emptyListDrafts);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [uploadingHeroField, setUploadingHeroField] = useState<keyof Pick<
    HomepagePreviewContent,
    "cover_image" | "video_url"
  > | null>(null);

  useEffect(() => {
    let cancelled = false;

    getSiteSettings()
      .then((nextSettings) => {
        if (cancelled) {
          return;
        }
        const normalizedSettings = {
          ...nextSettings,
          homepage_content: normalizeHomepageContent(nextSettings.homepage_content),
        };
        setSettings(normalizedSettings);
        setListDrafts(buildListDrafts(normalizedSettings));
        setError(null);
      })
      .catch((nextError) => {
        if (cancelled) {
          return;
        }
        setError(nextError instanceof Error ? nextError.message : "Failed to load homepage content");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  function updateRootField(field: RootHomepageTextField, value: string) {
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

  function updateHomepageField(field: HomepageTextField, value: string) {
    setSettings((current) =>
      current
        ? {
            ...current,
            homepage_content: {
              ...current.homepage_content,
              [field]: value,
            },
          }
        : current,
    );
  }

  function updateHomepageNumberField(
    field: "hero_title_rotating_interval_ms" | "hero_title_rotating_animation_ms",
    value: number,
  ) {
    setSettings((current) =>
      current
        ? {
            ...current,
            homepage_content: {
              ...current.homepage_content,
              [field]: value,
            },
          }
        : current,
    );
  }

  function updateHeroPreview(field: keyof HomepagePreviewContent, value: string | null) {
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
        : current,
    );
  }

  async function handleHeroPreviewUpload(
    field: keyof Pick<HomepagePreviewContent, "cover_image" | "video_url">,
    file: File | null,
  ) {
    if (!file || !tokens?.access_token || !settings) {
      return;
    }

    setUploadingHeroField(field);
    try {
      const asset = await uploadAsset(file, tokens.access_token, "site_settings", settings.id);
      setSettings((current) =>
        current
          ? {
              ...current,
              homepage_content: {
                ...current.homepage_content,
                hero_preview: {
                  ...current.homepage_content.hero_preview,
                  visual_variant: "uploaded-media",
                  [field]: asset.public_url,
                },
              },
            }
          : current,
      );
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to upload hero preview media");
    } finally {
      setUploadingHeroField(null);
    }
  }

  function updateListDraft(field: keyof ListDrafts, value: string) {
    setListDrafts((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSave() {
    if (!tokens?.access_token || !settings) {
      return;
    }

    setIsSaving(true);
    try {
      const settingsForSave = applyListDrafts(settings, listDrafts);
      const updated = await updateSiteSettings(buildSiteSettingsUpdatePayload(settingsForSave), tokens.access_token);
      const normalizedSettings = {
        ...updated,
        homepage_content: normalizeHomepageContent(updated.homepage_content),
      };
      setSettings(normalizedSettings);
      setListDrafts(buildListDrafts(normalizedSettings));
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to save homepage content");
    } finally {
      setIsSaving(false);
    }
  }

  if (!settings) {
    return (
      <SurfaceCard variant="elevated">
        <div className="space-y-3">
          <PillBadge tone={error ? "rose" : "subtle"}>{error ? "Homepage error" : "Loading"}</PillBadge>
          <p className={error ? "text-sm text-rose-700" : "text-sm text-[var(--text-secondary)]"}>
            {error ?? "Loading homepage content..."}
          </p>
        </div>
      </SurfaceCard>
    );
  }

  const content = normalizeHomepageContent(settings.homepage_content);

  return (
    <div className="space-y-7">
      <SectionHeader
        eyebrow="Content settings"
        title="Homepage settings"
        description="Editable public homepage content grouped by the real blocks of the page."
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
          <ContentCardHeader
            eyebrow="Header"
            title="Top navigation"
            description="Everything shown in the first row: localized name and contact button label."
          />
        }
      >
        <div className="grid gap-4 md:grid-cols-2">
          <TextInput
            label="Brand name RU"
            value={content.brand_name_ru}
            onChange={(event) => updateHomepageField("brand_name_ru", event.currentTarget.value)}
          />
          <TextInput
            label="Brand name EN"
            value={content.brand_name_en}
            onChange={(event) => updateHomepageField("brand_name_en", event.currentTarget.value)}
          />
          <TextInput
            label="Header CTA RU"
            value={content.header_cta_label_ru}
            onChange={(event) => updateHomepageField("header_cta_label_ru", event.currentTarget.value)}
          />
          <TextInput
            label="Header CTA EN"
            value={content.header_cta_label_en}
            onChange={(event) => updateHomepageField("header_cta_label_en", event.currentTarget.value)}
          />
        </div>
      </SurfaceCard>

      <SurfaceCard
        variant="tinted"
        header={
          <ContentCardHeader
            eyebrow="Hero"
            title="Intro, offer and technologies"
            description="Eyebrow items, main headline, supporting text, technology list and the large preview beside it."
          />
        }
      >
        <div className="grid gap-4 md:grid-cols-2">
          <TextInput
            label="Hero eyebrow items RU"
            description="Через запятую: ФРОНТЕНД, 3D, МОУШЕН"
            value={listDrafts.heroEyebrowRu}
            onChange={(event) => updateListDraft("heroEyebrowRu", event.currentTarget.value)}
          />
          <TextInput
            label="Hero eyebrow items EN"
            description="Comma-separated list: FRONTEND, 3D, MOTION"
            value={listDrafts.heroEyebrowEn}
            onChange={(event) => updateListDraft("heroEyebrowEn", event.currentTarget.value)}
          />
          <TextInput
            label="Skills / technologies"
            description="Comma-separated list"
            value={listDrafts.skills}
            onChange={(event) => updateListDraft("skills", event.currentTarget.value)}
          />
          <Textarea
            label="Hero title RU"
            minRows={3}
            value={settings.hero_title_ru}
            onChange={(event) => updateRootField("hero_title_ru", event.currentTarget.value)}
          />
          <Textarea
            label="Hero title EN"
            minRows={3}
            value={settings.hero_title_en}
            onChange={(event) => updateRootField("hero_title_en", event.currentTarget.value)}
          />
          <TextInput
            label="Hero rotating words RU"
            description="Через запятую: сайты, мобильные приложения, десктопные приложения"
            value={listDrafts.heroTitleRotatingRu}
            onChange={(event) => updateListDraft("heroTitleRotatingRu", event.currentTarget.value)}
          />
          <TextInput
            label="Hero rotating words EN"
            description="Comma-separated list: websites, mobile apps, desktop apps"
            value={listDrafts.heroTitleRotatingEn}
            onChange={(event) => updateListDraft("heroTitleRotatingEn", event.currentTarget.value)}
          />
          <NumberInput
            label="Hero rotating speed"
            description="Milliseconds between word changes."
            min={600}
            step={100}
            value={content.hero_title_rotating_interval_ms}
            onChange={(value) =>
              updateHomepageNumberField(
                "hero_title_rotating_interval_ms",
                typeof value === "number" ? value : 1800,
              )
            }
          />
          <NumberInput
            label="Hero word animation duration"
            description="Milliseconds for the word slide-in animation."
            min={200}
            step={100}
            value={content.hero_title_rotating_animation_ms}
            onChange={(value) =>
              updateHomepageNumberField(
                "hero_title_rotating_animation_ms",
                typeof value === "number" ? value : 900,
              )
            }
          />
          <TextInput
            label="Hero rotating color"
            description="CSS color for the animated part, for example #4f63f6."
            value={content.hero_title_rotating_accent_color}
            onChange={(event) => updateHomepageField("hero_title_rotating_accent_color", event.currentTarget.value)}
          />
          <Textarea
            label="Hero subtitle RU"
            minRows={4}
            value={settings.hero_subtitle_ru}
            onChange={(event) => updateRootField("hero_subtitle_ru", event.currentTarget.value)}
          />
          <Textarea
            label="Hero subtitle EN"
            minRows={4}
            value={settings.hero_subtitle_en}
            onChange={(event) => updateRootField("hero_subtitle_en", event.currentTarget.value)}
          />
          <TextInput
            label="Technologies label RU"
            value={content.technologies_label_ru}
            onChange={(event) => updateHomepageField("technologies_label_ru", event.currentTarget.value)}
          />
          <TextInput
            label="Technologies label EN"
            value={content.technologies_label_en}
            onChange={(event) => updateHomepageField("technologies_label_en", event.currentTarget.value)}
          />
          <Select
            label="Hero preview visual"
            data={showcaseVisualOptions}
            value={content.hero_preview.visual_variant}
            onChange={(value) => updateHeroPreview("visual_variant", value ?? "dashboard-dark")}
          />
          <TextInput
            label="Hero preview duration"
            value={content.hero_preview.video_duration}
            onChange={(event) => updateHeroPreview("video_duration", event.currentTarget.value)}
          />
          <TextInput
            label="Hero preview cover image URL"
            description="Used as video poster before playback."
            value={content.hero_preview.cover_image ?? ""}
            onChange={(event) => updateHeroPreview("cover_image", event.currentTarget.value)}
          />
          <FileInput
            label="Upload hero cover image"
            description="PNG, JPG, WebP or AVIF."
            accept="image/*"
            clearable
            disabled={uploadingHeroField !== null || !tokens?.access_token}
            placeholder={uploadingHeroField === "cover_image" ? "Uploading..." : "Choose image"}
            onChange={(file) => void handleHeroPreviewUpload("cover_image", file)}
          />
          <TextInput
            label="Hero preview video URL"
            description="When set, the homepage uses the real video player."
            value={content.hero_preview.video_url ?? ""}
            onChange={(event) => updateHeroPreview("video_url", event.currentTarget.value)}
          />
          <FileInput
            label="Upload hero video"
            description="MP4/WebM is recommended."
            accept="video/*"
            clearable
            disabled={uploadingHeroField !== null || !tokens?.access_token}
            placeholder={uploadingHeroField === "video_url" ? "Uploading..." : "Choose video"}
            onChange={(file) => void handleHeroPreviewUpload("video_url", file)}
          />
        </div>
      </SurfaceCard>

      <SurfaceCard
        variant="soft"
        header={
          <ContentCardHeader
            eyebrow="Footer"
            title="Bottom contact block"
            description="Text, labels and contact destinations used by the final call-to-action block."
          />
        }
      >
        <div className="grid gap-4 md:grid-cols-2">
          <Textarea
            label="Contact title RU"
            minRows={3}
            value={content.contact_title_ru}
            onChange={(event) => updateHomepageField("contact_title_ru", event.currentTarget.value)}
          />
          <Textarea
            label="Contact title EN"
            minRows={3}
            value={content.contact_title_en}
            onChange={(event) => updateHomepageField("contact_title_en", event.currentTarget.value)}
          />
          <Textarea
            label="Contact description RU"
            minRows={3}
            value={content.contact_description_ru}
            onChange={(event) => updateHomepageField("contact_description_ru", event.currentTarget.value)}
          />
          <Textarea
            label="Contact description EN"
            minRows={3}
            value={content.contact_description_en}
            onChange={(event) => updateHomepageField("contact_description_en", event.currentTarget.value)}
          />
          <TextInput
            label="Email button RU"
            value={content.email_label_ru}
            onChange={(event) => updateHomepageField("email_label_ru", event.currentTarget.value)}
          />
          <TextInput
            label="Email button EN"
            value={content.email_label_en}
            onChange={(event) => updateHomepageField("email_label_en", event.currentTarget.value)}
          />
          <TextInput
            label="Contact email"
            value={settings.contact_email}
            onChange={(event) => updateRootField("contact_email", event.currentTarget.value)}
          />
          {contactSocialLinks.map((item) => (
            <TextInput
              key={item.key}
              label={`${item.label} URL`}
              placeholder={item.placeholder}
              value={settings.socials[item.key] ?? ""}
              onChange={(event) => updateSocial(item.key, event.currentTarget.value)}
            />
          ))}
        </div>
      </SurfaceCard>

      <SurfaceCard
        variant="default"
        header={
          <ContentCardHeader
            eyebrow="Project rows"
            title="Portfolio row labels"
            description="Shared labels used inside project showcase rows."
          />
        }
      >
        <div className="grid gap-4 md:grid-cols-2">
          <TextInput
            label="Project stack label RU"
            value={content.project_stack_label_ru}
            onChange={(event) => updateHomepageField("project_stack_label_ru", event.currentTarget.value)}
          />
          <TextInput
            label="Project stack label EN"
            value={content.project_stack_label_en}
            onChange={(event) => updateHomepageField("project_stack_label_en", event.currentTarget.value)}
          />
          <TextInput
            label="Project demo button RU"
            value={content.project_demo_cta_label_ru}
            onChange={(event) => updateHomepageField("project_demo_cta_label_ru", event.currentTarget.value)}
          />
          <TextInput
            label="Project demo button EN"
            value={content.project_demo_cta_label_en}
            onChange={(event) => updateHomepageField("project_demo_cta_label_en", event.currentTarget.value)}
          />
        </div>
      </SurfaceCard>

    </div>
  );
}

function ContentCardHeader({
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
