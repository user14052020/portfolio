from app.domain.chat_context import StyleDirectionContext


class DiversityConstraintsBuilder:
    def build(self, style_history: list[StyleDirectionContext]) -> dict[str, list[str]]:
        recent = style_history[-5:]
        return {
            "avoid_previous_palette": self._unique([color for style in recent for color in style.palette]),
            "avoid_previous_silhouette": self._unique([style.silhouette for style in recent if style.silhouette]),
            "avoid_previous_hero_garments": self._unique(
                [garment for style in recent for garment in style.hero_garments if garment]
            ),
            "avoid_previous_composition": self._unique(
                [style.composition_type for style in recent if style.composition_type]
            ),
        }

    def to_prompt_items(self, style_history: list[StyleDirectionContext]) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for style in style_history[-5:]:
            title = style.style_name or "Style Direction"
            slug = style.style_id or title.lower().replace(" ", "-")
            items.append({"slug": slug, "title": title, "en": title, "ru": title})
        return items

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            lowered = value.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            result.append(value)
        return result
