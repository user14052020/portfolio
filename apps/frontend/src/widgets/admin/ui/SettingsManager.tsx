"use client";

import { Button, Stack, TextInput, Textarea } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getSiteSettings, updateSiteSettings } from "@/shared/api/client";
import type { SiteSettings } from "@/shared/api/types";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function SettingsManager() {
  const { tokens } = useAdminAuth();
  const [settings, setSettings] = useState<SiteSettings | null>(null);

  useEffect(() => {
    getSiteSettings().then(setSettings);
  }, []);

  if (!settings) {
    return <div className="text-sm text-slate-500">Loading settings...</div>;
  }

  return (
    <WindowFrame title="Site settings" subtitle="Global content">
      <Stack>
        <TextInput
          label="Brand name"
          value={settings.brand_name}
          onChange={(event) => setSettings({ ...settings, brand_name: event.currentTarget.value })}
        />
        <TextInput
          label="Contact email"
          value={settings.contact_email}
          onChange={(event) => setSettings({ ...settings, contact_email: event.currentTarget.value })}
        />
        <TextInput
          label="Assistant name RU"
          value={settings.assistant_name_ru}
          onChange={(event) => setSettings({ ...settings, assistant_name_ru: event.currentTarget.value })}
        />
        <TextInput
          label="Assistant name EN"
          value={settings.assistant_name_en}
          onChange={(event) => setSettings({ ...settings, assistant_name_en: event.currentTarget.value })}
        />
        <TextInput
          label="Hero title RU"
          value={settings.hero_title_ru}
          onChange={(event) => setSettings({ ...settings, hero_title_ru: event.currentTarget.value })}
        />
        <TextInput
          label="Hero title EN"
          value={settings.hero_title_en}
          onChange={(event) => setSettings({ ...settings, hero_title_en: event.currentTarget.value })}
        />
        <Textarea
          label="Hero subtitle RU"
          value={settings.hero_subtitle_ru}
          onChange={(event) => setSettings({ ...settings, hero_subtitle_ru: event.currentTarget.value })}
        />
        <Textarea
          label="Hero subtitle EN"
          value={settings.hero_subtitle_en}
          onChange={(event) => setSettings({ ...settings, hero_subtitle_en: event.currentTarget.value })}
        />
        <Textarea
          label="About text RU"
          value={settings.about_text_ru}
          onChange={(event) => setSettings({ ...settings, about_text_ru: event.currentTarget.value })}
        />
        <Textarea
          label="About text EN"
          value={settings.about_text_en}
          onChange={(event) => setSettings({ ...settings, about_text_en: event.currentTarget.value })}
        />
        <TextInput
          label="Skills"
          value={settings.skills.join(", ")}
          onChange={(event) =>
            setSettings({
              ...settings,
              skills: event.currentTarget.value.split(",").map((item) => item.trim()).filter(Boolean)
            })
          }
        />
        <Button
          radius="xl"
          onClick={async () => {
            if (!tokens?.access_token) {
              return;
            }
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
                skills: settings.skills
              },
              tokens.access_token
            );
            setSettings(updated);
          }}
        >
          Save settings
        </Button>
      </Stack>
    </WindowFrame>
  );
}
