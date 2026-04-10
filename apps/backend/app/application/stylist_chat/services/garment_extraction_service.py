from app.application.stylist_chat.contracts.ports import GarmentExtractor
from app.application.stylist_chat.services.constants import (
    COLOR_KEYWORDS,
    FIT_KEYWORDS,
    GARMENT_KEYWORDS,
    MATERIAL_KEYWORDS,
    SEASON_KEYWORDS,
)
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment


class RuleBasedGarmentExtractor(GarmentExtractor):
    CATEGORY_BY_GARMENT: dict[str, str] = {
        "shirt": "tops",
        "t-shirt": "tops",
        "blazer": "tailoring",
        "jacket": "outerwear",
        "coat": "outerwear",
        "hoodie": "tops",
        "sweater": "knitwear",
        "dress": "one_piece",
        "skirt": "bottoms",
        "trousers": "bottoms",
        "jeans": "bottoms",
        "sneakers": "footwear",
        "shoes": "footwear",
        "bag": "accessories",
    }

    PATTERN_KEYWORDS: dict[str, tuple[str, ...]] = {
        "striped": ("striped", "stripe", "полоск"),
        "checked": ("checked", "check", "клет"),
        "solid": ("solid", "plain", "однотон"),
    }

    STYLE_HINT_KEYWORDS: dict[str, tuple[str, ...]] = {
        "minimal": ("minimal", "миним"),
        "relaxed": ("relaxed", "расслаб", "свобод"),
        "oversized": ("oversized", "оверсайз"),
        "edgy": ("edgy", "кожан", "leather"),
        "smart": ("smart", "blazer", "пиджак"),
        "casual": ("casual", "деним", "denim"),
    }

    FORMALITY_KEYWORDS: dict[str, tuple[str, ...]] = {
        "formal": ("formal", "класс", "вечер"),
        "smart-casual": ("smart casual", "smart-casual", "смарт"),
        "casual": ("casual", "кэжуал", "повседнев"),
    }

    async def extract(
        self,
        user_text: str,
        asset_id: str | None = None,
        existing_anchor: AnchorGarment | None = None,
    ) -> AnchorGarment:
        existing_anchor = existing_anchor or AnchorGarment()
        raw_text = self._combine_text(existing_anchor.raw_user_text, user_text)
        lowered = raw_text.lower()

        garment_type = self.first_keyword_match(lowered, GARMENT_KEYWORDS) or existing_anchor.garment_type
        colors = self.all_keyword_matches(lowered, COLOR_KEYWORDS)
        material = self.first_keyword_match(lowered, MATERIAL_KEYWORDS) or existing_anchor.material
        fit = self.first_keyword_match(lowered, FIT_KEYWORDS) or existing_anchor.fit
        pattern = self.first_keyword_match(lowered, self.PATTERN_KEYWORDS) or existing_anchor.pattern
        seasonality = self.all_keyword_matches(lowered, SEASON_KEYWORDS) or list(existing_anchor.seasonality)
        style_hints = self.collect_style_hints(lowered, garment_type=garment_type, material=material, fit=fit)

        color_primary = colors[0] if colors else existing_anchor.color_primary or existing_anchor.color
        color_secondary = colors[1:] if len(colors) > 1 else list(existing_anchor.color_secondary or existing_anchor.secondary_colors)
        return AnchorGarment(
            raw_user_text=raw_text,
            garment_type=garment_type,
            category=self.CATEGORY_BY_GARMENT.get(garment_type or "", existing_anchor.category),
            color_primary=color_primary,
            color_secondary=color_secondary,
            material=material,
            fit=fit,
            silhouette=fit or existing_anchor.silhouette,
            pattern=pattern,
            seasonality=self.merge_unique(existing_anchor.seasonality, seasonality),
            formality=self.first_keyword_match(lowered, self.FORMALITY_KEYWORDS) or existing_anchor.formality,
            gender_context=existing_anchor.gender_context,
            style_hints=self.merge_unique(existing_anchor.style_hints, style_hints),
            asset_id=asset_id or existing_anchor.asset_id,
            confidence=self.calculate_confidence(
                garment_type=garment_type,
                colors=colors,
                material=material,
                fit=fit,
                pattern=pattern,
                asset_id=asset_id or existing_anchor.asset_id,
            ),
            completeness_score=existing_anchor.completeness_score,
            is_sufficient_for_generation=existing_anchor.is_sufficient_for_generation,
        )

    def calculate_confidence(
        self,
        *,
        garment_type: str | None,
        colors: list[str],
        material: str | None,
        fit: str | None,
        pattern: str | None,
        asset_id: str | None,
    ) -> float:
        confidence = 0.1
        confidence += 0.3 if garment_type else 0.0
        confidence += 0.15 if colors else 0.0
        confidence += 0.15 if material else 0.0
        confidence += 0.1 if fit else 0.0
        confidence += 0.05 if pattern else 0.0
        confidence += 0.15 if asset_id else 0.0
        return min(confidence, 0.95)

    def collect_style_hints(
        self,
        lowered_text: str,
        *,
        garment_type: str | None,
        material: str | None,
        fit: str | None,
    ) -> list[str]:
        hints = self.all_keyword_matches(lowered_text, self.STYLE_HINT_KEYWORDS)
        if material == "linen":
            hints.append("airy")
        if material == "denim":
            hints.append("casual")
        if garment_type == "blazer":
            hints.append("polished")
        if garment_type == "jacket" and material == "leather":
            hints.append("edgy")
        if fit == "oversized":
            hints.append("relaxed")
        return self.merge_unique([], hints)

    def first_keyword_match(self, lowered_text: str, mapping: dict[str, tuple[str, ...]]) -> str | None:
        for canonical, hints in mapping.items():
            if any(hint in lowered_text for hint in hints):
                return canonical
        return None

    def all_keyword_matches(self, lowered_text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
        matches: list[str] = []
        for canonical, hints in mapping.items():
            if any(hint in lowered_text for hint in hints):
                matches.append(canonical)
        return matches

    def merge_unique(self, base: list[str], extra: list[str]) -> list[str]:
        merged: list[str] = []
        for value in [*base, *extra]:
            cleaned = value.strip() if isinstance(value, str) else ""
            if cleaned and cleaned not in merged:
                merged.append(cleaned)
        return merged

    def _combine_text(self, existing_text: str | None, user_text: str) -> str:
        parts = [part.strip() for part in [existing_text or "", user_text or ""] if part and part.strip()]
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        if parts[0].lower() in parts[1].lower():
            return parts[1]
        return " ".join(parts)
