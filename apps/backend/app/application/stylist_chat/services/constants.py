from typing import Any


GENERATION_HINTS = (
    "generate",
    "render",
    "visualize",
    "visualise",
    "lookbook",
    "flat lay",
    "flat-lay",
    "сгенер",
    "визуал",
    "покажи",
)

GARMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "shirt": ("shirt", "рубаш"),
    "t-shirt": ("t-shirt", "tee", "футболк"),
    "blazer": ("blazer", "пиджак"),
    "jacket": ("jacket", "куртк"),
    "coat": ("coat", "пальто", "тренч"),
    "hoodie": ("hoodie", "толстовк", "худи"),
    "sweater": ("sweater", "jumper", "пуловер", "свитер"),
    "dress": ("dress", "плать"),
    "skirt": ("skirt", "юбк"),
    "trousers": ("trousers", "pants", "брюк"),
    "jeans": ("jeans", "джинс"),
    "sneakers": ("sneakers", "кроссовк"),
    "shoes": ("shoes", "boots", "ботин", "туфл"),
    "bag": ("bag", "сумк"),
}

COLOR_KEYWORDS: dict[str, tuple[str, ...]] = {
    "black": ("black", "черн"),
    "white": ("white", "бел"),
    "grey": ("grey", "gray", "сер"),
    "navy": ("navy", "темно-син", "тёмно-син"),
    "blue": ("blue", "син"),
    "beige": ("beige", "беж"),
    "brown": ("brown", "корич"),
    "green": ("green", "зелен", "зелён"),
    "red": ("red", "красн"),
}

MATERIAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "denim": ("denim", "джинс"),
    "linen": ("linen", "лен", "лён"),
    "cotton": ("cotton", "хлоп"),
    "wool": ("wool", "шерст"),
    "leather": ("leather", "кож"),
    "suede": ("suede", "замш"),
    "knit": ("knit", "трикот"),
}

FIT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "straight": ("straight", "прям"),
    "slim": ("slim", "притал"),
    "oversized": ("oversized", "оверсайз"),
    "relaxed": ("relaxed", "свобод"),
}

SEASON_KEYWORDS: dict[str, tuple[str, ...]] = {
    "spring": ("spring", "весн"),
    "summer": ("summer", "лет"),
    "autumn": ("autumn", "fall", "осен"),
    "winter": ("winter", "зим"),
}

TIME_OF_DAY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "morning": ("morning", "утр"),
    "day": ("day", "днем", "днём", "день"),
    "evening": ("evening", "вечер"),
    "night": ("night", "ноч"),
}

DRESS_CODE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "black tie": ("black tie",),
    "cocktail": ("cocktail", "коктейл"),
    "formal": ("formal", "формаль"),
    "smart casual": ("smart casual", "smart-casual", "смарт"),
    "casual": ("casual", "кэжуал", "повседнев"),
}

EVENT_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "wedding": ("wedding", "свад"),
    "date": ("date", "свидан"),
    "dinner": ("dinner", "ужин"),
    "office party": ("corporate", "корпоратив", "office party"),
    "theater": ("theater", "theatre", "театр"),
    "party": ("party", "вечерин"),
    "conference": ("conference", "конферен"),
    "birthday": ("birthday", "день рождения"),
}

IMPRESSION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "elegant": ("elegant", "элегант"),
    "confident": ("confident", "уверен"),
    "romantic": ("romantic", "романт"),
    "relaxed": ("relaxed", "расслаб"),
    "bold": ("bold", "смел"),
}

LOCATION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "restaurant": ("restaurant", "ресторан"),
    "outdoor": ("outdoor", "outside", "open air", "на улице"),
    "office": ("office", "офис"),
    "theater": ("theater", "theatre", "театр"),
    "beach": ("beach", "пляж"),
}

WEATHER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "cold": ("cold", "холод"),
    "warm": ("warm", "тепл", "тёпл"),
    "hot": ("hot", "жарк"),
    "rainy": ("rain", "rainy", "дожд"),
    "windy": ("wind", "ветр"),
}

FALLBACK_STYLE_LIBRARY: tuple[dict[str, Any], ...] = (
    {
        "style_id": "artful-minimalism",
        "style_name": "Artful Minimalism",
        "palette": ["chalk", "charcoal", "stone"],
        "silhouette": "clean and elongated",
        "hero_garments": ["structured coat", "fine knit", "straight trousers"],
        "footwear": ["sharp leather shoes"],
        "accessories": ["restrained watch"],
        "materials": ["wool", "cotton"],
        "styling_mood": "quiet and precise",
        "composition_type": "editorial flat lay",
        "background_family": "stone",
    },
    {
        "style_id": "soft-retro-prep",
        "style_name": "Soft Retro Prep",
        "palette": ["camel", "cream", "navy"],
        "silhouette": "relaxed collegiate layering",
        "hero_garments": ["oxford shirt", "textured knit", "pleated trousers"],
        "footwear": ["loafers"],
        "accessories": ["belt"],
        "materials": ["tweed", "cotton"],
        "styling_mood": "polished but warm",
        "composition_type": "editorial flat lay",
        "background_family": "paper",
    },
    {
        "style_id": "relaxed-workwear",
        "style_name": "Relaxed Workwear",
        "palette": ["olive", "ecru", "brown"],
        "silhouette": "grounded utility layers",
        "hero_garments": ["overshirt", "sturdy trousers", "simple tee"],
        "footwear": ["substantial boots"],
        "accessories": ["canvas belt"],
        "materials": ["canvas", "denim"],
        "styling_mood": "practical and calm",
        "composition_type": "editorial flat lay",
        "background_family": "wood",
    },
)
