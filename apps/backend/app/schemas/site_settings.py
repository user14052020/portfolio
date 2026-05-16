from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import TimestampedRead


class HomepagePreviewContent(BaseModel):
    visual_variant: str = "dashboard-dark"
    video_duration: str = "0:45"


class HomepageContent(BaseModel):
    brand_name_ru: str = "Вадим Махаррам"
    brand_name_en: str = "Vadim Makharram"
    hero_eyebrow_items: list[str] = Field(
        default_factory=lambda: ["FRONTEND", "3D", "MOTION"]
    )
    technologies_label_ru: str = "Технологии"
    technologies_label_en: str = "Technologies"
    project_stack_label_ru: str = "Стек"
    project_stack_label_en: str = "Stack"
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
    chat_section_title_ru: str = "AI-стилист"
    chat_section_title_en: str = "AI stylist"
    chat_section_description_ru: str = "Чат-бот временно вынесен в конец страницы."
    chat_section_description_en: str = "The chatbot block is temporarily placed at the end of the page."


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
