from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import TimestampedRead


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
