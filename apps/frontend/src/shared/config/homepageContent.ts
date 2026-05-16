import type { HomepageContent, ProjectShowcaseMeta } from "@/shared/api/types";

export type ShowcaseVisualVariant =
  | "dashboard-dark"
  | "dashboard-light"
  | "chair-3d"
  | "finance-motion"
  | "uploaded-media";

export const showcaseVisualOptions: Array<{ value: ShowcaseVisualVariant; label: string }> = [
  { value: "dashboard-dark", label: "Dark analytics dashboard" },
  { value: "dashboard-light", label: "Light analytics dashboard" },
  { value: "chair-3d", label: "Interactive 3D configurator" },
  { value: "finance-motion", label: "Purple motion interface" },
  { value: "uploaded-media", label: "Uploaded video or cover image" },
];

export const defaultHomepageContent: HomepageContent = {
  brand_name_ru: "Вадим Махаррам",
  brand_name_en: "Vadim Makharram",
  hero_eyebrow_items: ["FRONTEND", "3D", "MOTION"],
  technologies_label_ru: "Технологии",
  technologies_label_en: "Technologies",
  project_stack_label_ru: "Стек",
  project_stack_label_en: "Stack",
  hero_preview: {
    visual_variant: "dashboard-dark",
    video_duration: "0:45",
  },
  header_cta_label_ru: "Связаться со мной",
  header_cta_label_en: "Contact me",
  contact_title_ru: "Есть проект?\nДавайте обсудим",
  contact_title_en: "Have a project?\nLet's discuss",
  contact_description_ru: "Опишите задачу - предложу решение\nи подскажу оптимальный подход.",
  contact_description_en: "Describe the task - I will suggest a solution\nand the right implementation path.",
  telegram_label_ru: "Telegram",
  telegram_label_en: "Telegram",
  email_label_ru: "Email",
  email_label_en: "Email",
  chat_section_title_ru: "AI-стилист",
  chat_section_title_en: "AI stylist",
  chat_section_description_ru: "Чат-бот временно вынесен в конец страницы.",
  chat_section_description_en: "The chatbot block is temporarily placed at the end of the page.",
};

export const defaultProjectShowcaseMeta: ProjectShowcaseMeta = {
  visual_variant: "dashboard-light",
  video_duration: "0:40",
};

export function normalizeHomepageContent(content?: Partial<HomepageContent> | null): HomepageContent {
  return {
    ...defaultHomepageContent,
    ...content,
    hero_eyebrow_items:
      content?.hero_eyebrow_items && content.hero_eyebrow_items.length > 0
        ? content.hero_eyebrow_items
        : defaultHomepageContent.hero_eyebrow_items,
    hero_preview: {
      ...defaultHomepageContent.hero_preview,
      ...content?.hero_preview,
    },
  };
}

export function normalizeProjectShowcaseMeta(
  meta?: Partial<ProjectShowcaseMeta> | null,
  fallback?: Partial<ProjectShowcaseMeta>
): ProjectShowcaseMeta {
  return {
    ...defaultProjectShowcaseMeta,
    ...fallback,
    ...meta,
  };
}
