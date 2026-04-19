import type { BlogPost, Project, SiteSettings } from "@/shared/api/types";

export const fallbackSettings: SiteSettings = {
  id: 1,
  brand_name: "Vadim Creative Portfolio",
  contact_email: "hello@vadim.dev",
  contact_phone: "+7 (900) 000-00-00",
  assistant_name_ru: "Валентин",
  assistant_name_en: "Jose",
  hero_title_ru: "AI, full-stack и визуальные системы",
  hero_title_en: "AI, full-stack and visual systems",
  hero_subtitle_ru: "Проектирую и собираю digital-продукты на стыке backend, frontend, motion и генеративного AI.",
  hero_subtitle_en: "I architect and build digital products across backend, frontend, motion and generative AI.",
  about_title_ru: "Обо мне",
  about_title_en: "About me",
  about_text_ru: "Senior full-stack architect и lead developer.",
  about_text_en: "Senior full-stack architect and lead developer.",
  socials: {
    github: "https://github.com/example"
  },
  skills: ["FastAPI", "Next.js", "ComfyUI", "React Three Fiber"],
  message_cooldown_seconds: 60,
  try_other_style_cooldown_seconds: 60,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
};

export const fallbackProjects: Project[] = [];
export const fallbackPosts: BlogPost[] = [];
