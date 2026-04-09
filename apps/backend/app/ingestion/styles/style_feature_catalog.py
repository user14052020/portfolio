from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureVocabulary:
    trait_type: str
    values: dict[str, tuple[str, ...]]


COLOR_VOCABULARY = FeatureVocabulary(
    trait_type="color",
    values={
        "black": ("black", "jet black", "charcoal", "ebony"),
        "white": ("white", "ivory", "cream", "off-white", "off white"),
        "grey": ("grey", "gray", "ash grey", "ash gray", "slate"),
        "brown": ("brown", "camel", "tan", "beige", "taupe", "sepia", "mocha"),
        "red": ("red", "burgundy", "maroon", "scarlet", "crimson", "wine"),
        "pink": ("pink", "rose", "blush", "dusty pink", "fuchsia"),
        "orange": ("orange", "rust", "terracotta", "burnt orange", "amber"),
        "yellow": ("yellow", "mustard", "gold", "ochre"),
        "green": ("green", "olive", "sage", "emerald", "forest green", "khaki"),
        "blue": ("blue", "navy", "indigo", "cobalt", "powder blue", "teal"),
        "purple": ("purple", "violet", "lavender", "lilac", "plum"),
        "metallic": ("metallic", "silver", "golden", "chrome", "bronze"),
        "pastel": ("pastel", "pastel palette", "soft pastels"),
        "neon": ("neon", "fluorescent"),
    },
)

MATERIAL_VOCABULARY = FeatureVocabulary(
    trait_type="material",
    values={
        "denim": ("denim", "jean"),
        "tweed": ("tweed",),
        "wool": ("wool", "woolen", "knit wool"),
        "cotton": ("cotton", "canvas", "muslin", "poplin"),
        "linen": ("linen", "flax"),
        "silk": ("silk", "satin", "chiffon"),
        "leather": ("leather", "suede", "patent leather", "faux leather"),
        "lace": ("lace",),
        "velvet": ("velvet", "velour"),
        "corduroy": ("corduroy",),
        "cashmere": ("cashmere",),
        "fur": ("fur", "faux fur", "shearling"),
        "mesh": ("mesh", "fishnet", "netted"),
        "vinyl": ("vinyl", "pvc", "latex"),
    },
)

SILHOUETTE_VOCABULARY = FeatureVocabulary(
    trait_type="silhouette",
    values={
        "tailored": ("tailored", "structured", "sharp tailoring"),
        "oversized": ("oversized", "boxy", "slouchy"),
        "relaxed": ("relaxed", "loose fit", "easy fit"),
        "fitted": ("fitted", "bodycon", "close-fitting", "close fitting"),
        "layered": ("layered", "multi-layered", "layering"),
        "wide-leg": ("wide leg", "wide-leg", "flared"),
        "cropped": ("cropped", "shortened hem"),
        "flowy": ("flowy", "fluid", "draped"),
        "voluminous": ("voluminous", "puffy", "full skirt", "billowing"),
        "minimal": ("minimal silhouette", "clean lines", "streamlined"),
    },
)

GARMENT_VOCABULARY = FeatureVocabulary(
    trait_type="garment",
    values={
        "blazer": ("blazer", "sport coat"),
        "coat": ("coat", "overcoat", "trench", "pea coat", "puffer"),
        "jacket": ("jacket", "bomber", "varsity jacket", "overshirt"),
        "shirt": ("shirt", "button-up", "button down", "blouse"),
        "t-shirt": ("t-shirt", "tee", "graphic tee"),
        "sweater": ("sweater", "jumper", "knitwear", "cardigan"),
        "hoodie": ("hoodie", "sweatshirt"),
        "dress": ("dress", "gown", "slip dress", "sundress"),
        "skirt": ("skirt", "mini skirt", "midi skirt", "maxi skirt"),
        "trousers": ("trousers", "pants", "slacks"),
        "jeans": ("jeans", "denim pants"),
        "shorts": ("shorts",),
        "vest": ("vest", "waistcoat"),
        "corset": ("corset", "bustier"),
        "uniform": ("uniform", "school uniform", "military uniform"),
    },
)

FOOTWEAR_VOCABULARY = FeatureVocabulary(
    trait_type="footwear",
    values={
        "loafers": ("loafers",),
        "derbies": ("derbies", "oxfords", "brogues"),
        "boots": ("boots", "combat boots", "chelsea boots", "cowboy boots"),
        "sneakers": ("sneakers", "trainers", "tennis shoes"),
        "heels": ("heels", "pumps", "stilettos"),
        "sandals": ("sandals", "gladiator sandals"),
        "ballet flats": ("ballet flats", "flats"),
        "platforms": ("platforms", "platform shoes"),
    },
)

ACCESSORY_VOCABULARY = FeatureVocabulary(
    trait_type="accessory",
    values={
        "hat": ("hat", "beret", "cap", "beanie", "bonnet"),
        "scarf": ("scarf", "shawl"),
        "gloves": ("gloves",),
        "bag": ("bag", "handbag", "tote", "backpack", "satchel"),
        "belt": ("belt",),
        "tie": ("tie", "necktie", "bow tie"),
        "jewelry": ("jewelry", "jewellery", "necklace", "ring", "bracelet", "earrings"),
        "glasses": ("glasses", "eyewear", "sunglasses", "spectacles"),
        "stockings": ("stockings", "tights", "hosiery"),
    },
)

PATTERN_VOCABULARY = FeatureVocabulary(
    trait_type="motif",
    values={
        "plaid": ("plaid", "tartan", "checkered"),
        "stripes": ("stripes", "striped"),
        "floral": ("floral", "flower print", "botanical"),
        "polka dots": ("polka dot", "polka dots"),
        "animal print": ("animal print", "leopard print", "zebra print", "snakeskin"),
        "lacework": ("lacework", "embroidered lace"),
        "distressed": ("distressed", "ripped", "worn-in", "worn in"),
        "patchwork": ("patchwork",),
    },
)

MOOD_VOCABULARY = FeatureVocabulary(
    trait_type="mood",
    values={
        "romantic": ("romantic", "dreamy", "soft", "delicate"),
        "dark": ("dark", "moody", "gothic", "melancholic"),
        "intellectual": ("intellectual", "scholarly", "academic"),
        "playful": ("playful", "whimsical", "fun"),
        "rebellious": ("rebellious", "edgy", "punk", "defiant"),
        "elegant": ("elegant", "refined", "polished"),
        "nostalgic": ("nostalgic", "retro", "vintage", "old-fashioned"),
        "futuristic": ("futuristic", "sci-fi", "cyber", "space-age"),
        "natural": ("natural", "earthy", "organic"),
        "minimal": ("minimal", "clean", "understated"),
    },
)

OCCASION_VOCABULARY = FeatureVocabulary(
    trait_type="occasion",
    values={
        "formal": ("formal", "black tie", "evening wear"),
        "office": ("office", "business", "workwear"),
        "casual": ("casual", "everyday", "daywear"),
        "party": ("party", "club", "night out"),
        "outdoor": ("outdoor", "hiking", "camping"),
        "ceremony": ("wedding", "ceremony", "reception"),
        "gallery": ("gallery", "museum", "art show", "exhibition"),
        "school": ("school", "campus", "college"),
    },
)

ERA_VOCABULARY = FeatureVocabulary(
    trait_type="era",
    values={
        "victorian": ("victorian",),
        "edwardian": ("edwardian",),
        "1920s": ("1920s", "1920's", "twenties", "roaring twenties"),
        "1950s": ("1950s", "1950's", "fifties"),
        "1960s": ("1960s", "1960's", "sixties"),
        "1970s": ("1970s", "1970's", "seventies"),
        "1980s": ("1980s", "1980's", "eighties"),
        "1990s": ("1990s", "1990's", "nineties"),
        "2000s": ("2000s", "2000's", "y2k"),
        "medieval": ("medieval", "middle ages"),
    },
)

REGION_VOCABULARY = FeatureVocabulary(
    trait_type="region",
    values={
        "japan": ("japan", "japanese", "harajuku"),
        "korea": ("korea", "korean", "seoul"),
        "france": ("france", "french", "parisian"),
        "italy": ("italy", "italian"),
        "britain": ("britain", "british", "england", "english"),
        "america": ("america", "american", "usa", "united states"),
        "scandinavia": ("scandinavia", "scandinavian", "nordic"),
        "eastern europe": ("eastern europe", "slavic"),
    },
)

SUBCULTURE_VOCABULARY = FeatureVocabulary(
    trait_type="subculture",
    values={
        "punk": ("punk",),
        "goth": ("goth", "gothic"),
        "grunge": ("grunge",),
        "emo": ("emo",),
        "hippie": ("hippie", "bohemian"),
        "prep": ("prep", "preppy"),
        "skater": ("skater", "skate"),
        "raver": ("raver", "rave"),
        "lolita": ("lolita",),
    },
)

ART_REFERENCE_VOCABULARY = FeatureVocabulary(
    trait_type="art_reference",
    values={
        "art nouveau": ("art nouveau",),
        "art deco": ("art deco",),
        "baroque": ("baroque",),
        "rococo": ("rococo",),
        "surrealism": ("surrealism", "surrealist"),
        "minimalism": ("minimalism", "minimalist"),
        "avant-garde": ("avant-garde", "avant garde"),
        "romanticism": ("romanticism", "romantic art"),
        "modernism": ("modernism", "modernist"),
    },
)

SEASONALITY_VOCABULARY = FeatureVocabulary(
    trait_type="seasonality",
    values={
        "spring": ("spring", "vernal"),
        "summer": ("summer", "warm weather", "hot weather"),
        "autumn": ("autumn", "fall", "harvest"),
        "winter": ("winter", "cold weather", "frost"),
        "all-season": ("all season", "all-season", "year-round", "year round"),
        "transitional": ("transitional", "in-between seasons", "between seasons"),
    },
)

HAIR_MAKEUP_VOCABULARY = FeatureVocabulary(
    trait_type="hair_makeup",
    values={
        "natural makeup": ("natural makeup", "minimal makeup", "barely-there makeup"),
        "dark makeup": ("dark makeup", "smokey eye", "smoky eye", "dark eyeliner"),
        "soft blush": ("soft blush", "rosy cheeks", "pink blush"),
        "red lips": ("red lips", "red lipstick", "bold lip"),
        "glossy lips": ("glossy lips", "lip gloss"),
        "braids": ("braids", "braided hair"),
        "bangs": ("bangs", "fringe"),
        "sleek hair": ("sleek hair", "slicked-back hair", "slicked back hair"),
        "loose waves": ("loose waves", "soft waves", "wavy hair"),
        "curls": ("curls", "curly hair", "ringlets"),
    },
)

COMPOSITION_HINT_VOCABULARY = FeatureVocabulary(
    trait_type="composition_hint",
    values={
        "monochrome": ("monochrome", "tonal dressing", "single-color look", "single color look"),
        "high contrast": ("high contrast", "strong contrast", "sharp contrast"),
        "layered styling": ("layered styling", "heavy layering", "multiple layers"),
        "minimal styling": ("minimal styling", "pared-back styling", "pared back styling"),
        "maximal styling": ("maximal styling", "ornate styling", "decorative styling"),
        "tailored structure": ("tailored structure", "structured composition", "structured look"),
        "soft drape": ("soft drape", "fluid composition", "draped composition"),
        "texture mixing": ("mixed textures", "texture mixing", "textural contrast"),
    },
)


FEATURE_VOCABULARIES: tuple[FeatureVocabulary, ...] = (
    COLOR_VOCABULARY,
    MATERIAL_VOCABULARY,
    SILHOUETTE_VOCABULARY,
    GARMENT_VOCABULARY,
    FOOTWEAR_VOCABULARY,
    ACCESSORY_VOCABULARY,
    PATTERN_VOCABULARY,
    MOOD_VOCABULARY,
    OCCASION_VOCABULARY,
    ERA_VOCABULARY,
    REGION_VOCABULARY,
    SUBCULTURE_VOCABULARY,
    ART_REFERENCE_VOCABULARY,
    SEASONALITY_VOCABULARY,
    HAIR_MAKEUP_VOCABULARY,
    COMPOSITION_HINT_VOCABULARY,
)
