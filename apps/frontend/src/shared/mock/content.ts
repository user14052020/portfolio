import type { SiteSettings } from "@/shared/api/types";
import { defaultHomepageContent } from "@/shared/config/homepageContent";

const fallbackTimestamp = new Date().toISOString();

export const fallbackSettings: SiteSettings = {
  id: 1,
  brand_name: "Вадим Махаррам",
  contact_email: "hello@vadim.dev",
  contact_phone: "+7 (900) 000-00-00",
  assistant_name_ru: "Валентин",
  assistant_name_en: "Jose",
  hero_title_ru: "Разрабатываю веб-продукты с 3D-графикой и motion-интерфейсами",
  hero_title_en: "I build web products with 3D graphics and motion interfaces",
  hero_subtitle_ru: "Создаю быстрые, интерактивные и визуально продуманные решения для бизнеса и стартапов.",
  hero_subtitle_en: "I create fast, interactive and visually considered solutions for businesses and startups.",
  about_title_ru: "Обо мне",
  about_title_en: "About me",
  about_text_ru: "Senior full-stack architect и lead developer.",
  about_text_en: "Senior full-stack architect and lead developer.",
  socials: {
    telegram: "https://t.me/example",
    vk: "",
    youtube: "",
    rutube: "",
    dzen: "",
    github: "https://github.com/example"
  },
  skills: ["TypeScript", "Next.js", "Three.js", "GSAP", "Framer Motion"],
  homepage_content: defaultHomepageContent,
  chat_bot_enabled: false,
  message_cooldown_seconds: 60,
  try_other_style_cooldown_seconds: 60,
  created_at: fallbackTimestamp,
  updated_at: fallbackTimestamp
};
