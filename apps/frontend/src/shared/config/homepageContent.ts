import type { HomepageContent, ProjectShowcaseMeta, SiteMetaContent } from "@/shared/api/types";

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

export const defaultSiteMetaContent: SiteMetaContent = {
  title_ru: "Вадим Махаррам - веб-продукты с 3D и motion",
  title_en: "Vadim Makharram - web products with 3D and motion",
  description_ru:
    "Разрабатываю быстрые веб-продукты с 3D-графикой, motion-интерфейсами и продуманной архитектурой.",
  description_en:
    "I build fast web products with 3D graphics, motion interfaces and thoughtful architecture.",
  keywords: ["frontend", "3d", "motion", "next.js", "three.js", "portfolio"],
  canonical_url: "https://maharram.ru",
  og_title_ru: "Вадим Махаррам",
  og_title_en: "Vadim Makharram",
  og_description_ru: "Веб-продукты с 3D-графикой и motion-интерфейсами.",
  og_description_en: "Web products with 3D graphics and motion interfaces.",
  og_image: null,
  twitter_card: "summary_large_image",
  theme_color: "#f7f7f5",
  robots_index: true,
  robots_follow: true,
};

export const defaultHomepageContent: HomepageContent = {
  brand_name_ru: "Вадим Махаррам",
  brand_name_en: "Vadim Makharram",
  hero_eyebrow_items: ["FRONTEND", "3D", "MOTION"],
  hero_eyebrow_items_ru: ["ФРОНТЕНД", "3D", "МОУШЕН"],
  hero_eyebrow_items_en: ["FRONTEND", "3D", "MOTION"],
  hero_title_rotating_items_ru: [
    "сайты",
    "мобильные приложения",
    "десктопные приложения",
    "3D-анимацию",
    "графический дизайн для видео",
  ],
  hero_title_rotating_items_en: [
    "websites",
    "mobile apps",
    "desktop apps",
    "3D animation",
    "video graphic design",
  ],
  hero_title_rotating_interval_ms: 1800,
  hero_title_rotating_animation_ms: 900,
  hero_title_rotating_accent_color: "#4f63f6",
  technologies_label_ru: "Технологии",
  technologies_label_en: "Technologies",
  project_stack_label_ru: "Стек",
  project_stack_label_en: "Stack",
  project_demo_cta_label_ru: "Нажмите, чтобы увидеть демо",
  project_demo_cta_label_en: "Click to view demo",
  hero_preview: {
    visual_variant: "dashboard-dark",
    video_duration: "0:45",
    video_url: null,
    cover_image: null,
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
  site_meta: defaultSiteMetaContent,
};

export const defaultProjectShowcaseMeta: ProjectShowcaseMeta = {
  visual_variant: "dashboard-light",
  video_duration: "0:40",
};

export function normalizeHomepageContent(content?: Partial<HomepageContent> | null): HomepageContent {
  const legacyHeroEyebrowItems =
    content?.hero_eyebrow_items && content.hero_eyebrow_items.length > 0
      ? content.hero_eyebrow_items
      : defaultHomepageContent.hero_eyebrow_items_en;
  const heroEyebrowItemsRu =
    content?.hero_eyebrow_items_ru && content.hero_eyebrow_items_ru.length > 0
      ? content.hero_eyebrow_items_ru
      : defaultHomepageContent.hero_eyebrow_items_ru;
  const heroEyebrowItemsEn =
    content?.hero_eyebrow_items_en && content.hero_eyebrow_items_en.length > 0
      ? content.hero_eyebrow_items_en
      : legacyHeroEyebrowItems;
  const heroTitleRotatingItemsRu =
    content?.hero_title_rotating_items_ru && content.hero_title_rotating_items_ru.length > 0
      ? content.hero_title_rotating_items_ru
      : defaultHomepageContent.hero_title_rotating_items_ru;
  const heroTitleRotatingItemsEn =
    content?.hero_title_rotating_items_en && content.hero_title_rotating_items_en.length > 0
      ? content.hero_title_rotating_items_en
      : defaultHomepageContent.hero_title_rotating_items_en;
  const rotatingInterval = Number(content?.hero_title_rotating_interval_ms);
  const rotatingAnimation = Number(content?.hero_title_rotating_animation_ms);

  return {
    ...defaultHomepageContent,
    ...content,
    hero_eyebrow_items: heroEyebrowItemsEn,
    hero_eyebrow_items_ru: heroEyebrowItemsRu,
    hero_eyebrow_items_en: heroEyebrowItemsEn,
    hero_title_rotating_items_ru: heroTitleRotatingItemsRu,
    hero_title_rotating_items_en: heroTitleRotatingItemsEn,
    hero_title_rotating_interval_ms:
      Number.isFinite(rotatingInterval) && rotatingInterval > 0
        ? Math.max(600, Math.round(rotatingInterval))
        : defaultHomepageContent.hero_title_rotating_interval_ms,
    hero_title_rotating_animation_ms:
      Number.isFinite(rotatingAnimation) && rotatingAnimation > 0
        ? Math.max(200, Math.round(rotatingAnimation))
        : defaultHomepageContent.hero_title_rotating_animation_ms,
    hero_title_rotating_accent_color:
      content?.hero_title_rotating_accent_color?.trim() ||
      defaultHomepageContent.hero_title_rotating_accent_color,
    hero_preview: {
      ...defaultHomepageContent.hero_preview,
      ...content?.hero_preview,
      video_url: content?.hero_preview?.video_url?.trim() || null,
      cover_image: content?.hero_preview?.cover_image?.trim() || null,
    },
    site_meta: {
      ...defaultSiteMetaContent,
      ...content?.site_meta,
      keywords:
        content?.site_meta?.keywords && content.site_meta.keywords.length > 0
          ? content.site_meta.keywords
          : defaultSiteMetaContent.keywords,
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
