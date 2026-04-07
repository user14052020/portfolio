import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.style_directions import style_directions_repository


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "styles"
STYLE_SOURCES: tuple[tuple[str, Path], ...] = (
    ("styles-1", DATA_DIR / "styles-1.txt"),
    ("styles-2", DATA_DIR / "styles-2.txt"),
)

TOKEN_TRANSLATIONS_RU = {
    "abstract": "абстрактный",
    "academia": "академия",
    "acid": "эйсид",
    "age": "эйдж",
    "alt": "альт",
    "american": "американский",
    "analog": "аналоговый",
    "androgynous": "андрогинный",
    "angel": "ангельский",
    "anime": "аниме",
    "anti": "анти",
    "apocalyptic": "апокалиптический",
    "art": "арт",
    "arts": "артс",
    "athleisure": "атлежер",
    "atomic": "атомный",
    "autumn": "осенний",
    "avant": "авангардный",
    "avant-garde": "авангард",
    "baroque": "барокко",
    "basic": "базовый",
    "beach": "пляжный",
    "beat": "бит",
    "beatnik": "битник",
    "black": "черный",
    "blue": "синий",
    "boho": "бохо",
    "bohemian": "богемный",
    "bold": "смелый",
    "boy": "бой",
    "bright": "яркий",
    "brit": "брит",
    "business": "бизнес",
    "casual": "кэжуал",
    "chic": "шик",
    "classic": "классика",
    "club": "клубный",
    "coastal": "прибрежный",
    "college": "колледж",
    "collegiate": "коллегиальный",
    "cool": "кул",
    "core": "кор",
    "cottage": "коттеджный",
    "country": "кантри",
    "cowboy": "ковбойский",
    "craft": "крафт",
    "dark": "темный",
    "deco": "деко",
    "design": "дизайн",
    "disco": "диско",
    "dress": "дресс",
    "edwardian": "эдвардианский",
    "elegance": "элегантность",
    "ethnic": "этнический",
    "euro": "евро",
    "fandom": "фандомный",
    "fashion": "мода",
    "formal": "формальный",
    "future": "будущий",
    "futurism": "футуризм",
    "futurist": "футуристический",
    "garden": "садовый",
    "girl": "герл",
    "girly": "девчачий",
    "glam": "глэм",
    "goth": "гот",
    "gothic": "готический",
    "grunge": "гранж",
    "heritage": "херитедж",
    "hip": "хип",
    "hippie": "хиппи",
    "history": "история",
    "house": "хаус",
    "indie": "инди",
    "industrial": "индастриал",
    "ivy": "айви",
    "japanese": "японский",
    "kawaii": "кавай",
    "kid": "кид",
    "ladylike": "ледилайк",
    "light": "светлый",
    "lounge": "лаунж",
    "lux": "люкс",
    "maximalism": "максимализм",
    "maximalist": "максималистичный",
    "metal": "метал",
    "metalhead": "металхед",
    "military": "милитари",
    "minimal": "минимал",
    "minimalism": "минимализм",
    "minimalist": "минималистичный",
    "modern": "современный",
    "mod": "мод",
    "mom": "мама",
    "neo": "нео",
    "new": "новый",
    "night": "ночной",
    "noir": "нуар",
    "nostalgia": "ностальгия",
    "office": "офисный",
    "old": "олд",
    "pastel": "пастельный",
    "party": "пати",
    "pioneer": "пионерский",
    "polish": "полиш",
    "pop": "поп",
    "post": "пост",
    "prep": "преп",
    "preppy": "преппи",
    "professional": "профессиональный",
    "punk": "панк",
    "quiet": "спокойный",
    "rave": "рейв",
    "retro": "ретро",
    "romantic": "романтичный",
    "romanticism": "романтизм",
    "scene": "сцена",
    "scandinavian": "скандинавский",
    "school": "школьный",
    "sharp": "собранный",
    "ski": "ски",
    "sleaze": "слиз",
    "smart": "смарт",
    "soft": "мягкий",
    "sport": "спорт",
    "sporty": "спортивный",
    "street": "стрит",
    "streetwear": "стритвир",
    "suburbia": "субурбия",
    "summer": "летний",
    "tech": "тех",
    "techno": "техно",
    "urban": "городской",
    "vintage": "винтаж",
    "western": "вестерн",
    "white": "белый",
    "work": "рабочий",
    "workout": "тренировочный",
    "workwear": "ворквир",
    "y2k": "y2k",
    "yoga": "йога",
}

PHRASE_TRANSLATIONS_RU = {
    "business casual": "бизнес-кэжуал",
    "business formal": "бизнес-формал",
    "business professional": "деловой профессиональный",
    "smart casual": "смарт-кэжуал",
    "after hours": "вечерний городской",
    "art deco": "ар-деко",
    "art nouveau": "ар-нуво",
    "black ivy": "черный айви",
    "bon chic, bon genre": "бон шик, бон жанр",
    "cool girl": "кул-герл",
    "cool boy": "кул-бой",
    "cottage core": "коттеджкор",
    "dark fandom": "темный фандом",
    "dark academia": "дарк-академия",
    "light academia": "лайт-академия",
    "new romanticism": "новый романтизм",
    "power dressing": "силовой дрессинг",
    "soft kawaii": "мягкий кавай",
    "summer nostalgia": "летняя ностальгия",
}

UNSUITABLE_STYLE_TERMS = {
    "bondage",
    "cannibal",
    "fetish",
    "furry",
    "gore",
    "horror",
    "loli",
    "lolita",
    "porn",
    "slut",
}

DESCRIPTOR_OVERRIDES = {
    "business casual": "polished separates, practical layers, and a smart relaxed silhouette",
    "preppy": "clean layers, collegiate texture, and polished casual structure",
    "minimalism": "clean lines, restrained palette, and calm wardrobe logic",
    "bohemian": "soft texture, fluid layers, and artisanal detail",
    "streetwear": "relaxed proportions, clear statement layers, and contemporary casual energy",
    "workwear": "sturdy fabrics, practical layers, and grounded structure",
}


@dataclass(frozen=True)
class StyleSeedRecord:
    slug: str
    source_title: str
    source_group: str
    title_en: str
    title_ru: str
    descriptor_en: str
    is_active: bool
    selection_weight: int
    sort_order: int


def _repair_text(value: str) -> str:
    text = value.strip().replace("\ufeff", "")
    if not text:
        return ""
    # Fix common mojibake when UTF-8 text was decoded as cp1252/latin-1.
    if any(marker in text for marker in ("Ã", "â", "Ð", "Ñ")):
        for encoding in ("latin-1", "cp1252"):
            try:
                repaired = text.encode(encoding).decode("utf-8")
            except UnicodeError:
                continue
            if repaired and repaired != text:
                text = repaired
                break
    return unicodedata.normalize("NFKC", text)


def normalize_style_title(value: str) -> str:
    text = _repair_text(value)
    text = re.sub(r"\s+", " ", text).strip(" -\t")
    return text


def build_display_style_title(value: str) -> str:
    title = normalize_style_title(value)
    title = re.sub(r"\([^)]*\)", "", title)
    title = re.sub(r"\s+", " ", title).strip(" -/\t")
    return title or normalize_style_title(value)


def build_style_slug(value: str) -> str:
    normalized = normalize_style_title(value)
    ascii_value = (
        unicodedata.normalize("NFKD", normalized)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    ascii_value = ascii_value.replace("&", " and ")
    ascii_value = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return ascii_value or "style"


def _transliterate_token(token: str) -> str:
    mapping = {
        "a": "а",
        "b": "б",
        "c": "к",
        "d": "д",
        "e": "е",
        "f": "ф",
        "g": "г",
        "h": "х",
        "i": "и",
        "j": "дж",
        "k": "к",
        "l": "л",
        "m": "м",
        "n": "н",
        "o": "о",
        "p": "п",
        "q": "к",
        "r": "р",
        "s": "с",
        "t": "т",
        "u": "у",
        "v": "в",
        "w": "в",
        "x": "кс",
        "y": "й",
        "z": "з",
    }
    result: list[str] = []
    for char in token.lower():
        result.append(mapping.get(char, char))
    return "".join(result)


def translate_style_title_to_ru(value: str) -> str:
    title = normalize_style_title(value)
    lowered = title.lower()

    for phrase, translation in sorted(PHRASE_TRANSLATIONS_RU.items(), key=lambda item: len(item[0]), reverse=True):
        if lowered == phrase:
            return translation

    parts = re.split(r"(\W+)", title)
    translated_parts: list[str] = []
    for part in parts:
        if not part:
            continue
        if re.fullmatch(r"\W+", part):
            translated_parts.append(part)
            continue

        lowered_part = part.lower()
        translated = TOKEN_TRANSLATIONS_RU.get(lowered_part)
        if translated is None:
            translated = _transliterate_token(part) if re.search(r"[A-Za-z]", part) else part
        translated_parts.append(translated)

    return "".join(translated_parts).strip() or title


def build_style_descriptor(title_en: str) -> str:
    lowered = title_en.lower()
    for key, descriptor in DESCRIPTOR_OVERRIDES.items():
        if key in lowered:
            return descriptor

    core = title_en.strip()
    return f"{core}, wearable fashion direction, one coherent wardrobe mood"


def is_style_recommendable(title_en: str) -> bool:
    lowered = title_en.lower()
    return not any(term in lowered for term in UNSUITABLE_STYLE_TERMS)


def build_selection_weight(source_group: str, title_en: str) -> int:
    base_weight = 120 if source_group == "styles-1" else 90
    lowered = title_en.lower()
    if "core" in lowered:
        base_weight -= 15
    if "business" in lowered or "casual" in lowered or "minimal" in lowered or "preppy" in lowered:
        base_weight += 20
    return max(base_weight, 10)


def load_style_seed_records() -> list[StyleSeedRecord]:
    records_by_slug: dict[str, StyleSeedRecord] = {}
    sort_order = 1
    for source_group, path in STYLE_SOURCES:
        if not path.exists():
            continue

        raw_lines = path.read_text(encoding="utf-8").splitlines()
        for raw_line in raw_lines:
            source_title = normalize_style_title(raw_line)
            title_en = build_display_style_title(source_title)
            if not title_en:
                continue
            slug = build_style_slug(title_en)
            candidate = StyleSeedRecord(
                slug=slug,
                source_title=source_title,
                source_group=source_group,
                title_en=title_en,
                title_ru=translate_style_title_to_ru(title_en),
                descriptor_en=build_style_descriptor(title_en),
                is_active=is_style_recommendable(title_en),
                selection_weight=build_selection_weight(source_group, title_en),
                sort_order=sort_order,
            )
            sort_order += 1

            existing = records_by_slug.get(slug)
            if existing is None or (existing.source_group != "styles-1" and source_group == "styles-1"):
                records_by_slug[slug] = candidate

    return sorted(records_by_slug.values(), key=lambda item: (item.sort_order, item.slug))


async def seed_style_catalog(session: AsyncSession) -> tuple[int, int]:
    created = 0
    updated = 0
    for record in load_style_seed_records():
        existing = await style_directions_repository.get_by_slug(session, record.slug)
        payload = {
            "slug": record.slug,
            "source_title": record.source_title,
            "source_group": record.source_group,
            "title_en": record.title_en,
            "title_ru": record.title_ru,
            "descriptor_en": record.descriptor_en,
            "selection_weight": record.selection_weight,
            "sort_order": record.sort_order,
            "is_active": record.is_active,
        }
        if existing is None:
            await style_directions_repository.create(session, payload)
            created += 1
        else:
            await style_directions_repository.update(session, existing, payload)
            updated += 1
    return created, updated
