import type { SiteSettings } from "@/shared/api/types";
import { normalizeHomepageContent } from "@/shared/config/homepageContent";

export function buildSiteSettingsUpdatePayload(settings: SiteSettings): Record<string, unknown> {
  return {
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
  };
}
