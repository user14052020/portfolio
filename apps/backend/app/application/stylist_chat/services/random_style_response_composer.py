import re
from typing import Any

from app.domain.style_exploration.entities.style_direction import StyleDirection


class RandomStyleResponseComposer:
    """Builds deterministic user-facing prose for random style exploration."""

    MIN_SENTENCES = 7
    MAX_SENTENCES = 10
    HISTORY_SENTENCES = 3

    def compose(
        self,
        *,
        locale: str,
        style_direction: StyleDirection,
        source_model: Any | None,
    ) -> str:
        title = self._style_title(style_direction=style_direction, source_model=source_model)
        history_sentences = self._history_sentences(
            locale=locale,
            title=title,
            source_model=source_model,
        )
        sentences = self._localized_facet_sentences(
            locale=locale,
            title=title,
            style_direction=style_direction,
            source_model=source_model,
        )
        source_sentences = [] if locale == "ru" else self._source_description_sentences(source_model)
        sentences = [
            *history_sentences,
            *source_sentences,
            *sentences,
        ]
        sentences = self._unique(sentences)[: self.MAX_SENTENCES]
        if len(sentences) < self.MIN_SENTENCES:
            sentences = self._unique(
                [
                    *sentences,
                    *self._fallback_sentences(
                        locale=locale,
                        title=title,
                        style_direction=style_direction,
                    ),
                ]
            )[: self.MAX_SENTENCES]

        heading = (
            f"\u0421\u043b\u0443\u0447\u0430\u0439\u043d\u044b\u0439 \u0441\u0442\u0438\u043b\u044c: {title}."
            if locale == "ru"
            else f"Random style: {title}."
        )
        return f"{heading}\n\n{' '.join(sentences[: self.MAX_SENTENCES])}"

    def _localized_facet_sentences(
        self,
        *,
        locale: str,
        title: str,
        style_direction: StyleDirection,
        source_model: Any | None,
    ) -> list[str]:
        metadata = self._metadata(source_model)
        distinct_points = self._string_list(metadata.get("what_makes_it_distinct"))
        core_logic = self._string_list(metadata.get("core_style_logic"))
        styling_rules = self._string_list(metadata.get("styling_rules"))
        palette = self._values(style_direction.palette, metadata.get("palette"))
        garments = self._values(
            style_direction.hero_garments,
            metadata.get("hero_garments"),
            metadata.get("garments"),
            metadata.get("statement_pieces"),
        )
        footwear = self._values(style_direction.footwear, metadata.get("shoes"), metadata.get("footwear"))
        accessories = self._values(
            style_direction.accessories,
            metadata.get("core_accessories"),
            metadata.get("accessories"),
        )
        materials = self._values(style_direction.materials, metadata.get("materials"))
        mood = self._values(style_direction.styling_mood, metadata.get("mood_keywords"))
        silhouette = style_direction.silhouette_family or self._optional_text(metadata.get("silhouette_family"))

        if locale == "ru":
            return [
                f"\u0415\u0433\u043e \u0441\u0438\u043b\u0443\u044d\u0442\u043d\u0430\u044f \u043b\u043e\u0433\u0438\u043a\u0430: {silhouette}." if silhouette else "",
                self._ru_list_sentence("\u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u0432\u0435\u0449\u0438", garments),
                self._ru_list_sentence("\u041f\u0430\u043b\u0438\u0442\u0440\u0430", palette),
                self._ru_list_sentence("\u041c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b", materials),
                self._ru_list_sentence("\u041e\u0431\u0443\u0432\u044c", footwear),
                self._ru_list_sentence("\u0410\u043a\u0441\u0435\u0441\u0441\u0443\u0430\u0440\u044b", accessories),
                self._ru_list_sentence("\u041d\u0430\u0441\u0442\u0440\u043e\u0435\u043d\u0438\u0435", mood),
                *self._ru_detail_sentences(distinct_points, core_logic, styling_rules),
                self._ru_visual_sentence(style_direction),
            ]

        return [
            f"Its silhouette logic is {silhouette}." if silhouette else "",
            self._en_list_sentence("Key garments", garments),
            self._en_list_sentence("Palette", palette),
            self._en_list_sentence("Materials", materials),
            self._en_list_sentence("Footwear", footwear),
            self._en_list_sentence("Accessories", accessories),
            self._en_list_sentence("Mood", mood),
            *self._en_detail_sentences(distinct_points, core_logic, styling_rules),
            self._en_visual_sentence(style_direction),
        ]

    def _fallback_sentences(
        self,
        *,
        locale: str,
        title: str,
        style_direction: StyleDirection,
    ) -> list[str]:
        if locale == "ru":
            return [
                f"\u042d\u0442\u043e\u0442 \u0441\u0442\u0438\u043b\u044c \u0432\u0430\u0436\u0435\u043d \u043d\u0435 \u043e\u0434\u043d\u043e\u0439 \u0432\u0435\u0449\u044c\u044e, \u0430 \u0441\u0432\u044f\u0437\u044c\u044e \u0441\u0438\u043b\u0443\u044d\u0442\u0430, \u0444\u0430\u043a\u0442\u0443\u0440\u044b \u0438 \u0446\u0432\u0435\u0442\u0430.",
                "\u0414\u043b\u044f \u0432\u0438\u0437\u0443\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u0438 \u044f \u0431\u0435\u0440\u0443 \u043e\u0434\u0438\u043d \u0446\u0435\u043b\u044c\u043d\u044b\u0439 flat lay, \u0431\u0435\u0437 \u043b\u0438\u0448\u043d\u0438\u0445 \u0434\u0443\u0431\u043b\u0435\u0439 \u0438 \u0441\u043b\u0443\u0447\u0430\u0439\u043d\u044b\u0445 \u043f\u0440\u0435\u0434\u043c\u0435\u0442\u043e\u0432.",
                f"\u041d\u0430 \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044e \u0443\u0445\u043e\u0434\u0438\u0442 \u0438\u043c\u0435\u043d\u043d\u043e {title}, \u0430 \u043d\u0435 \u043e\u0431\u0449\u0438\u0439 \u043d\u0430\u0431\u043e\u0440 \u0432\u0435\u0449\u0435\u0439.",
            ]
        return [
            "The style matters through the relationship between silhouette, texture, and color rather than one isolated item.",
            "For visualization I will use one coherent flat lay without duplicate categories or random props.",
            f"The generation is anchored to {title}, not to a generic outfit bundle.",
            self._en_visual_sentence(style_direction),
        ]

    def _history_sentences(
        self,
        *,
        locale: str,
        title: str,
        source_model: Any | None,
    ) -> list[str]:
        metadata = self._metadata(source_model)
        historical_notes = self._string_list(metadata.get("historical_notes"))
        era = self._string_list(metadata.get("era"))
        origin_regions = self._string_list(metadata.get("origin_regions"))
        platforms = self._string_list(metadata.get("platforms"))
        brands = self._string_list(metadata.get("brands"))
        related_styles = self._string_list(metadata.get("related_styles"))
        overlap_styles = self._string_list(metadata.get("overlap_styles"))
        definition = self._optional_text(metadata.get("core_definition"))

        raw_sentences = [
            *historical_notes[:2],
            definition,
            self._joined_context("era", era),
            self._joined_context("origin", origin_regions),
            self._joined_context("platforms", platforms),
            self._joined_context("brands", brands),
            self._joined_context("related styles", related_styles or overlap_styles),
        ]
        cleaned = [item for item in raw_sentences if item]

        if locale == "ru":
            return self._ru_history_sentences(
                title=title,
                historical_notes=historical_notes,
                era=era,
                origin_regions=origin_regions,
                platforms=platforms,
                brands=brands,
                related_styles=related_styles or overlap_styles,
                definition=definition,
            )[: self.HISTORY_SENTENCES]

        sentences = []
        if definition:
            sentences.append(f"Historically, {definition.rstrip('.')}.")
        for note in historical_notes[:2]:
            sentences.append(f"The source history notes that {self._lowercase_first(note.rstrip('.'))}.")
        if era or origin_regions:
            parts = []
            if era:
                parts.append(f"era: {', '.join(era[:3])}")
            if origin_regions:
                parts.append(f"origin: {', '.join(origin_regions[:3])}")
            sentences.append(f"Its period context is {', '.join(parts)}.")
        if platforms or brands:
            markers = [*platforms[:3], *brands[:3]]
            sentences.append(f"Culturally, it travels through {', '.join(markers)}.")
        if related_styles or overlap_styles:
            sentences.append(f"It sits near {', '.join((related_styles or overlap_styles)[:4])}.")
        if not sentences and cleaned:
            sentences.extend(f"Historically, {item.rstrip('.')}." for item in cleaned[: self.HISTORY_SENTENCES])
        if not sentences:
            sentences.append(
                f"Historically, {title} is treated here as a documented style direction rather than a random outfit label."
            )
        return sentences[: self.HISTORY_SENTENCES]

    def _ru_history_sentences(
        self,
        *,
        title: str,
        historical_notes: list[str],
        era: list[str],
        origin_regions: list[str],
        platforms: list[str],
        brands: list[str],
        related_styles: list[str],
        definition: str | None,
    ) -> list[str]:
        sentences: list[str] = []
        if era or origin_regions:
            parts = []
            if era:
                parts.append(f"\u043f\u0435\u0440\u0438\u043e\u0434: {', '.join(era[:3])}")
            if origin_regions:
                parts.append(f"\u0441\u0440\u0435\u0434\u0430: {', '.join(origin_regions[:3])}")
            sentences.append(f"\u041f\u043e \u043f\u0440\u043e\u0438\u0441\u0445\u043e\u0436\u0434\u0435\u043d\u0438\u044e \u044d\u0442\u043e {', '.join(parts)}.")
        if platforms or brands:
            markers = [*platforms[:3], *brands[:3]]
            sentences.append(f"\u041a\u0443\u043b\u044c\u0442\u0443\u0440\u043d\u044b\u0435 \u043c\u0430\u0440\u043a\u0435\u0440\u044b \u0441\u0442\u0438\u043b\u044f: {', '.join(markers)}.")
        if related_styles:
            sentences.append(f"\u041f\u043e \u0441\u043e\u0441\u0435\u0434\u043d\u0438\u043c \u043d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f\u043c \u043e\u043d \u0441\u0432\u044f\u0437\u0430\u043d \u0441 {', '.join(related_styles[:4])}.")

        localized_notes = [note for note in historical_notes if self._has_cyrillic(note)]
        for note in localized_notes[:2]:
            sentences.append(f"\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a \u0444\u0438\u043a\u0441\u0438\u0440\u0443\u0435\u0442 \u0432\u0430\u0436\u043d\u044b\u0439 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442: {note.rstrip('.')}.")
        if definition and self._has_cyrillic(definition):
            sentences.append(f"\u0418\u0441\u0442\u043e\u0440\u0438\u0447\u0435\u0441\u043a\u0438 {title} \u0432 \u0431\u0430\u0437\u0435 \u043e\u043f\u0438\u0441\u0430\u043d \u0442\u0430\u043a: {definition.rstrip('.')}.")
        if len(sentences) < self.HISTORY_SENTENCES and (historical_notes or definition):
            sentences.append(
                f"\u0418\u0441\u0442\u043e\u0440\u0438\u0447\u0435\u0441\u043a\u0438 {title} \u043e\u043f\u0438\u0440\u0430\u0435\u0442\u0441\u044f \u043d\u0430 \u0434\u043e\u043d\u043e\u0440\u0441\u043a\u043e\u0435 \u043e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0438\u0437 \u0431\u0430\u0437\u044b, \u043f\u043e\u044d\u0442\u043e\u043c\u0443 \u043d\u0435 \u0441\u043e\u0431\u0438\u0440\u0430\u0435\u0442\u0441\u044f \u043a\u0430\u043a \u0441\u043b\u0443\u0447\u0430\u0439\u043d\u044b\u0439 \u043d\u0430\u0431\u043e\u0440 \u0432\u0435\u0449\u0435\u0439."
            )
        if len(sentences) < self.HISTORY_SENTENCES:
            sentences.append(
                f"\u0418\u0441\u0442\u043e\u0440\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442 {title} \u044f \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u044e \u043a\u0430\u043a \u0440\u0430\u043c\u043a\u0443 \u0434\u043b\u044f \u0441\u0438\u043b\u0443\u044d\u0442\u0430, \u0432\u0435\u0449\u0435\u0439, \u043f\u0430\u043b\u0438\u0442\u0440\u044b \u0438 \u0432\u0438\u0437\u0443\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u0438."
            )
        if not sentences:
            sentences.append(
                f"\u0418\u0441\u0442\u043e\u0440\u0438\u0447\u0435\u0441\u043a\u0438 {title} \u0437\u0434\u0435\u0441\u044c \u0432\u0437\u044f\u0442 \u043a\u0430\u043a \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u043e\u0435 \u0441\u0442\u0438\u043b\u0435\u0432\u043e\u0435 \u043d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435, \u0430 \u043d\u0435 \u0441\u043b\u0443\u0447\u0430\u0439\u043d\u044b\u0439 \u043d\u0430\u0431\u043e\u0440 \u0432\u0435\u0449\u0435\u0439."
            )
        return sentences

    def _source_description_sentences(self, source_model: Any | None) -> list[str]:
        metadata = self._metadata(source_model)
        text_parts = [
            self._optional_text(getattr(source_model, "body", None)),
            self._optional_text(metadata.get("style_catalog_body")),
            self._optional_text(getattr(source_model, "summary", None)),
            self._optional_text(metadata.get("presentation_one_sentence_description")),
            self._optional_text(metadata.get("presentation_short_explanation")),
            self._optional_text(metadata.get("core_definition")),
            self._optional_text(metadata.get("fashion_summary")),
            self._optional_text(metadata.get("visual_summary")),
        ]
        sentences: list[str] = []
        for text in text_parts:
            if not text:
                continue
            sentences.extend(self._split_sentences(text))
            if len(sentences) >= self.MAX_SENTENCES:
                break
        return sentences

    def _ru_detail_sentences(
        self,
        distinct_points: list[str],
        core_logic: list[str],
        styling_rules: list[str],
    ) -> list[str]:
        details = [*distinct_points[:2], *core_logic[:2], *styling_rules[:2]]
        return [
            f"\u0412 \u043e\u043f\u0438\u0441\u0430\u043d\u0438\u0438 \u0432\u0430\u0436\u043d\u043e: {detail}."
            for detail in details
            if detail
        ]

    def _en_detail_sentences(
        self,
        distinct_points: list[str],
        core_logic: list[str],
        styling_rules: list[str],
    ) -> list[str]:
        details = [*distinct_points[:2], *core_logic[:2], *styling_rules[:2]]
        return [f"The description emphasizes {detail}." for detail in details if detail]

    def _ru_visual_sentence(self, style_direction: StyleDirection) -> str:
        bits = [
            style_direction.composition_type,
            style_direction.background_family,
            style_direction.layout_density,
            style_direction.camera_distance,
        ]
        rendered = ", ".join(bit for bit in bits if bit)
        return (
            f"\u0412\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u043e \u044d\u0442\u043e \u0443\u0445\u043e\u0434\u0438\u0442 \u0432 {rendered}."
            if rendered
            else "\u0412\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u043e \u044d\u0442\u043e \u0443\u0445\u043e\u0434\u0438\u0442 \u0432 \u0446\u0435\u043b\u044c\u043d\u044b\u0439 editorial flat lay."
        )

    def _en_visual_sentence(self, style_direction: StyleDirection) -> str:
        bits = [
            style_direction.composition_type,
            style_direction.background_family,
            style_direction.layout_density,
            style_direction.camera_distance,
        ]
        rendered = ", ".join(bit for bit in bits if bit)
        return (
            f"Visually, this goes into {rendered}."
            if rendered
            else "Visually, this goes into one coherent editorial flat lay."
        )

    def _joined_context(self, label: str, values: list[str]) -> str | None:
        return f"{label}: {', '.join(values[:4])}" if values else None

    def _style_title(self, *, style_direction: StyleDirection, source_model: Any | None) -> str:
        metadata = self._metadata(source_model)
        return (
            style_direction.style_name
            or self._optional_text(metadata.get("style_name"))
            or self._optional_text(getattr(source_model, "title", None))
            or "Style Direction"
        )

    def _metadata(self, source_model: Any | None) -> dict[str, Any]:
        metadata = getattr(source_model, "metadata", None)
        return metadata if isinstance(metadata, dict) else {}

    def _values(self, primary: list[str], *fallbacks: object) -> list[str]:
        values: list[str] = []
        for source in (primary, *fallbacks):
            for item in self._string_list(source):
                if item.lower() not in {existing.lower() for existing in values}:
                    values.append(item)
        return values[:4]

    def _ru_list_sentence(self, label: str, values: list[str]) -> str:
        return f"{label}: {', '.join(values)}." if values else ""

    def _en_list_sentence(self, label: str, values: list[str]) -> str:
        return f"{label}: {', '.join(values)}." if values else ""

    def _split_sentences(self, value: str) -> list[str]:
        normalized = " ".join(value.split()).strip()
        if not normalized:
            return []
        parts = re.split(r"(?<=[.!?])\s+", normalized)
        return [part.strip() for part in parts if len(part.strip()) > 20]

    def _optional_text(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = " ".join(value.split()).strip()
        return cleaned or None

    def _lowercase_first(self, text: str) -> str:
        if not text:
            return text
        if text.startswith("I ") or text.startswith("I'"):
            return text
        return text[:1].lower() + text[1:]

    def _has_cyrillic(self, text: str) -> bool:
        return any("\u0400" <= char <= "\u04ff" for char in text)

    def _string_list(self, value: object) -> list[str]:
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = self._optional_text(value)
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
        return result
