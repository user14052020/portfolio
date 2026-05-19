"use client";

import { Switch, Textarea, TextInput } from "@mantine/core";
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
import { ParserAdminPanel } from "@/widgets/admin/ui/ParserAdminPanel";
import { StyleIngestionSettingsManager } from "@/widgets/admin/ui/StyleIngestionSettingsManager";
import { StylistRuntimeSettingsManager } from "@/widgets/admin/ui/StylistRuntimeSettingsManager";

type AssistantNameField = "assistant_name_ru" | "assistant_name_en";
type ChatContentField =
  | "chat_section_title_ru"
  | "chat_section_title_en"
  | "chat_section_description_ru"
  | "chat_section_description_en";

export function RuntimeSettingsManager() {
  return (
    <div className="space-y-7">
      <SectionHeader
        eyebrow="Runtime"
        title="Parser and chatbot settings"
        description="Operational controls for the paused chatbot, public assistant limits and style-ingestion parser."
      />

      <ChatBotSettingsCard />
      <StylistRuntimeSettingsManager />
      <StyleIngestionSettingsManager />
      <ParserAdminPanel />
    </div>
  );
}

function ChatBotSettingsCard() {
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
        setError(nextError instanceof Error ? nextError.message : "Failed to load chatbot settings");
      });

    return () => {
      cancelled = true;
    };
  }, []);

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
      setError(nextError instanceof Error ? nextError.message : "Failed to save chatbot settings");
    } finally {
      setIsSaving(false);
    }
  }

  function updateAssistantName(field: AssistantNameField, value: string) {
    setSettings((current) => (current ? { ...current, [field]: value } : current));
  }

  function updateChatContent(field: ChatContentField, value: string) {
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

  const content = settings ? normalizeHomepageContent(settings.homepage_content) : null;

  return (
    <SurfaceCard
      variant="elevated"
      header={
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              <PillBadge tone="dark">Chatbot</PillBadge>
              <PillBadge tone={settings?.chat_bot_enabled ? "success" : "neutral"}>
                {settings?.chat_bot_enabled ? "Enabled" : "Paused"}
              </PillBadge>
            </div>
            <div>
              <h2 className="font-display text-2xl text-[var(--text-primary)]">Chatbot content and visibility</h2>
              <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
                Assistant names, homepage chatbot section copy and the public visibility flag.
              </p>
            </div>
          </div>
          <SoftButton tone="dark" onClick={handleSave} disabled={isSaving || !tokens?.access_token || !settings}>
            {isSaving ? "Saving..." : "Save chatbot settings"}
          </SoftButton>
        </div>
      }
    >
      {settings && content ? (
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_280px]">
            <div className="rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-5">
              <Switch
                label="Show chatbot block on the public homepage"
                description="When disabled, the chatbot UI is hidden but all runtime settings stay available here."
                checked={settings.chat_bot_enabled}
                onChange={(event) =>
                  setSettings((current) =>
                    current ? { ...current, chat_bot_enabled: event.currentTarget.checked } : current,
                  )
                }
              />
            </div>
            <div className="rounded-[24px] border border-[var(--border-soft)] bg-white/70 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Current state</p>
              <p className="mt-3 font-display text-3xl text-[var(--text-primary)]">
                {settings.chat_bot_enabled ? "Visible" : "Hidden"}
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <TextInput
              label="Assistant name RU"
              value={settings.assistant_name_ru}
              onChange={(event) => updateAssistantName("assistant_name_ru", event.currentTarget.value)}
            />
            <TextInput
              label="Assistant name EN"
              value={settings.assistant_name_en}
              onChange={(event) => updateAssistantName("assistant_name_en", event.currentTarget.value)}
            />
            <Textarea
              label="Chat section title RU"
              minRows={2}
              value={content.chat_section_title_ru}
              onChange={(event) => updateChatContent("chat_section_title_ru", event.currentTarget.value)}
            />
            <Textarea
              label="Chat section title EN"
              minRows={2}
              value={content.chat_section_title_en}
              onChange={(event) => updateChatContent("chat_section_title_en", event.currentTarget.value)}
            />
            <Textarea
              label="Chat section description RU"
              minRows={3}
              value={content.chat_section_description_ru}
              onChange={(event) => updateChatContent("chat_section_description_ru", event.currentTarget.value)}
            />
            <Textarea
              label="Chat section description EN"
              minRows={3}
              value={content.chat_section_description_en}
              onChange={(event) => updateChatContent("chat_section_description_en", event.currentTarget.value)}
            />
          </div>
        </div>
      ) : (
        <p className={error ? "text-sm text-rose-700" : "text-sm text-[var(--text-secondary)]"}>
          {error ?? "Loading chatbot settings..."}
        </p>
      )}

      {settings && error ? (
        <div className="mt-4 rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}
    </SurfaceCard>
  );
}
