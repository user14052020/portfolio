from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import TimestampedRead


class HomepagePreviewContent(BaseModel):
    enabled: bool = True
    visual_variant: str = "dashboard-dark"
    video_duration: str = "0:45"
    video_url: str | None = None
    cover_image: str | None = None


class SiteMetaContent(BaseModel):
    title_ru: str = "Вадим Махаррам - веб-продукты с 3D и motion"
    title_en: str = "Vadim Makharram - web products with 3D and motion"
    description_ru: str = (
        "Разрабатываю быстрые веб-продукты с 3D-графикой, motion-интерфейсами и продуманной архитектурой."
    )
    description_en: str = (
        "I build fast web products with 3D graphics, motion interfaces and thoughtful architecture."
    )
    keywords: list[str] = Field(
        default_factory=lambda: ["frontend", "3d", "motion", "next.js", "three.js", "portfolio"]
    )
    canonical_url: str | None = "https://maharram.ru"
    og_title_ru: str = "Вадим Махаррам"
    og_title_en: str = "Vadim Makharram"
    og_description_ru: str = "Веб-продукты с 3D-графикой и motion-интерфейсами."
    og_description_en: str = "Web products with 3D graphics and motion interfaces."
    og_image: str | None = None
    twitter_card: str = "summary_large_image"
    theme_color: str = "#f7f7f5"
    robots_index: bool = True
    robots_follow: bool = True


class HomepageContent(BaseModel):
    brand_name_ru: str = "Вадим Махаррам"
    brand_name_en: str = "Vadim Makharram"
    hero_eyebrow_items: list[str] = Field(
        default_factory=lambda: ["FRONTEND", "3D", "MOTION"]
    )
    hero_eyebrow_items_ru: list[str] = Field(
        default_factory=lambda: ["ФРОНТЕНД", "3D", "МОУШЕН"]
    )
    hero_eyebrow_items_en: list[str] = Field(
        default_factory=lambda: ["FRONTEND", "3D", "MOTION"]
    )
    hero_title_rotating_items_ru: list[str] = Field(
        default_factory=lambda: [
            "сайты",
            "мобильные приложения",
            "десктопные приложения",
            "3D-анимацию",
            "графический дизайн для видео",
        ]
    )
    hero_title_rotating_items_en: list[str] = Field(
        default_factory=lambda: [
            "websites",
            "mobile apps",
            "desktop apps",
            "3D animation",
            "video graphic design",
        ]
    )
    hero_title_rotating_interval_ms: int = 1800
    hero_title_rotating_animation_ms: int = 900
    hero_title_rotating_accent_color: str = "#4f63f6"
    technologies_label_ru: str = "Технологии"
    technologies_label_en: str = "Technologies"
    project_stack_label_ru: str = "Стек"
    project_stack_label_en: str = "Stack"
    project_demo_cta_label_ru: str = "Нажмите, чтобы увидеть демо"
    project_demo_cta_label_en: str = "Click to view demo"
    hero_preview: HomepagePreviewContent = Field(default_factory=HomepagePreviewContent)
    header_cta_label_ru: str = "Связаться со мной"
    header_cta_label_en: str = "Contact me"
    contact_title_ru: str = "Есть проект?\nДавайте обсудим"
    contact_title_en: str = "Have a project?\nLet's discuss"
    contact_description_ru: str = (
        "Опишите задачу - предложу решение\nи подскажу оптимальный подход."
    )
    contact_description_en: str = (
        "Describe the task - I will suggest a solution\nand the right implementation path."
    )
    telegram_label_ru: str = "Telegram"
    telegram_label_en: str = "Telegram"
    email_label_ru: str = "Email"
    email_label_en: str = "Email"
    kwork_reviews_eyebrow_ru: str = "Отзывы Kwork"
    kwork_reviews_eyebrow_en: str = "Kwork reviews"
    kwork_reviews_title_ru: str = "Отзывы о моей работе на площадке kwork.ru"
    kwork_reviews_title_en: str = "Reviews of my work on kwork.ru"
    chat_section_title_ru: str = "AI-стилист"
    chat_section_title_en: str = "AI stylist"
    chat_section_description_ru: str = "Чат-бот временно вынесен в конец страницы."
    chat_section_description_en: str = "The chatbot block is temporarily placed at the end of the page."
    site_meta: SiteMetaContent = Field(default_factory=SiteMetaContent)


class SiteSettingsUpdate(BaseModel):
    brand_name: str
    contact_email: EmailStr
    contact_phone: str | None = None
    assistant_name_ru: str
    assistant_name_en: str
    hero_title_ru: str
    hero_title_en: str
    hero_subtitle_ru: str
    hero_subtitle_en: str
    about_title_ru: str
    about_title_en: str
    about_text_ru: str
    about_text_en: str
    socials: dict[str, str] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    homepage_content: HomepageContent = Field(default_factory=HomepageContent)
    chat_bot_enabled: bool = False


class SiteSettingsRead(TimestampedRead):
    id: int
    brand_name: str
    contact_email: EmailStr
    contact_phone: str | None = None
    assistant_name_ru: str
    assistant_name_en: str
    hero_title_ru: str
    hero_title_en: str
    hero_subtitle_ru: str
    hero_subtitle_en: str
    about_title_ru: str
    about_title_en: str
    about_text_ru: str
    about_text_en: str
    socials: dict[str, str]
    skills: list[str]
    homepage_content: HomepageContent
    chat_bot_enabled: bool
    message_cooldown_seconds: int
    try_other_style_cooldown_seconds: int
