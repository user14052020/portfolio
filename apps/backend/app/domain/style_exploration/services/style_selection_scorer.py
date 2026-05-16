from app.domain.profile.policies.presentation_profile_item_policy import PresentationProfileItemPolicy
from app.domain.style_exploration.entities.style_direction import StyleDirection
from app.domain.style_exploration.entities.style_selection_profile import StyleSelectionProfile


class StyleSelectionScorer:
    PRESENTATION_TERMS = {
        "feminine": {"dress", "feminine", "heel", "skirt", "soft"},
        "masculine": {
            "blazer",
            "boot",
            "chino",
            "derby",
            "loafer",
            "menswear",
            "masculine",
            "shirt",
            "suit",
            "tailored",
            "trouser",
        },
        "androgynous": {"androgynous", "fluid", "genderless", "minimal", "unisex"},
        "unisex": {"neutral", "relaxed", "unisex", "universal", "versatile"},
    }
    WEARABILITY_TERMS = {
        "wearable": {
            "classic",
            "clean",
            "minimal",
            "neutral",
            "practical",
            "prep",
            "quiet",
            "tailored",
            "timeless",
            "wearable",
        },
        "balanced": {
            "balanced",
            "modern",
            "polished",
            "relaxed",
            "smart",
            "soft",
            "versatile",
        },
        "expressive": {
            "art",
            "artful",
            "avant",
            "bold",
            "dramatic",
            "experimental",
            "gallery",
            "maximal",
            "statement",
            "striking",
        },
    }
    SILHOUETTE_TERMS = {
        "relaxed": {"casual", "ease", "loose", "relaxed", "soft", "unstructured"},
        "tailored": {"clean", "crisp", "elongated", "sharp", "structured", "tailored"},
        "oversized": {"boxy", "oversized", "slouch", "volume", "wide"},
        "fluid": {"drape", "draped", "flowing", "fluid", "soft", "unstructured"},
    }
    PALETTE_TERMS = {
        "neutral": {
            "beige",
            "camel",
            "charcoal",
            "cream",
            "gray",
            "grey",
            "ivory",
            "navy",
            "neutral",
            "white",
        },
        "dark": {"black", "burgundy", "charcoal", "dark", "ink", "navy", "onyx"},
        "colorful": {"blue", "bold", "color", "green", "pink", "purple", "red", "saturated", "yellow"},
        "soft": {"blush", "cream", "ivory", "light", "pastel", "powder", "soft"},
    }
    MOOD_TERMS = {
        "minimal": {"clean", "minimal", "quiet", "restraint", "simple"},
        "romantic": {"poetic", "romantic", "soft", "vintage"},
        "street": {"denim", "sneaker", "street", "urban", "workwear"},
        "classic": {"classic", "prep", "tailored", "timeless", "traditional"},
        "artful": {"art", "artful", "avant", "editorial", "experimental", "gallery"},
    }

    def __init__(
        self,
        *,
        presentation_item_policy: PresentationProfileItemPolicy | None = None,
    ) -> None:
        self.presentation_item_policy = presentation_item_policy or PresentationProfileItemPolicy()

    def score(self, *, style: StyleDirection, profile: StyleSelectionProfile | None) -> float:
        if profile is None or not profile.has_signal():
            return 0.0
        haystack = self._style_text(style)
        score = 0.0
        if profile.presentation_profile:
            score += self._term_score(
                haystack,
                self.PRESENTATION_TERMS[profile.presentation_profile],
                weight=0.8,
            )
            incompatible_count = self.presentation_item_policy.incompatible_item_count(
                presentation_profile=profile.presentation_profile,
                items_by_category={
                    "garment": style.hero_garments,
                    "footwear": style.footwear,
                    "accessory": style.accessories,
                },
            )
            score -= incompatible_count * 1.6
        if profile.wearability:
            score += self._term_score(
                haystack,
                self.WEARABILITY_TERMS[profile.wearability],
                weight=1.2,
            )
        if profile.silhouette:
            score += self._term_score(
                haystack,
                self.SILHOUETTE_TERMS[profile.silhouette],
                weight=1.0,
            )
        if profile.palette:
            palette_text = " ".join(style.palette).lower()
            score += self._term_score(
                palette_text or haystack,
                self.PALETTE_TERMS[profile.palette],
                weight=0.9,
            )
        if profile.mood:
            score += self._term_score(haystack, self.MOOD_TERMS[profile.mood], weight=1.0)
        return round(score, 3)

    def _style_text(self, style: StyleDirection) -> str:
        parts = [
            style.style_id,
            style.style_name,
            style.style_family,
            style.silhouette_family,
            *style.palette,
            *style.hero_garments,
            *style.footwear,
            *style.accessories,
            *style.materials,
            *style.styling_mood,
            style.composition_type,
            style.background_family,
            style.layout_density,
            style.camera_distance,
            style.visual_preset,
        ]
        return " ".join(str(part).lower() for part in parts if part)

    def _term_score(self, text: str, terms: set[str], *, weight: float) -> float:
        if not text:
            return 0.0
        matches = sum(1 for term in terms if term in text)
        if matches == 0:
            return 0.0
        return min(matches, 3) * weight
