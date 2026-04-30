from app.domain.prompt_building.entities.compiled_image_prompt import CompiledImagePrompt
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.infrastructure.prompt_templates.registry import get_prompt_template


class ImagePromptCompiler:
    async def compile(self, *, brief: FashionBrief) -> CompiledImagePrompt:
        template = get_prompt_template(brief.brief_mode)
        style_tags = [brief.style_identity, *([brief.style_family] if brief.style_family else [])]
        palette_tags = list(brief.palette)
        garment_tags = [*brief.garment_list, *brief.footwear[:2], *brief.accessories[:2]]
        composition_tags = list(brief.composition_rules)
        prompt_sections = [
            template["base_prompt"],
            template["mode_prompt"],
            f"Style identity: {brief.style_identity}.",
            f"Historical reference: {'; '.join(brief.historical_reference[:2])}." if brief.historical_reference else "",
            f"Tailoring logic: {'; '.join(brief.tailoring_logic[:3])}." if brief.tailoring_logic else "",
            f"Color logic: {'; '.join(brief.color_logic[:3])}." if brief.color_logic else "",
            *self._profile_prompt_lines(brief),
            f"Garments: {', '.join(brief.garment_list[:5])}." if brief.garment_list else "",
            f"Palette: {', '.join(brief.palette[:4])}." if brief.palette else "",
            f"Materials: {', '.join(brief.materials[:4])}." if brief.materials else "",
            f"Footwear: {', '.join(brief.footwear[:2])}." if brief.footwear else "",
            f"Accessories: {', '.join(brief.accessories[:2])}." if brief.accessories else "",
            f"Styling notes: {'; '.join(brief.styling_notes[:3])}." if brief.styling_notes else "",
            f"Composition rules: {'; '.join(brief.composition_rules[:4])}." if brief.composition_rules else "",
            f"Visual preset: {brief.visual_preset or template['default_visual_preset']}.",
        ]
        negative_sections = [
            template["base_negative_prompt"],
            *brief.negative_constraints[:6],
            *self._profile_negative_lines(brief),
            *self._diversity_negative_lines(brief),
        ]
        compiled = CompiledImagePrompt(
            final_prompt=" ".join(" ".join(section for section in prompt_sections if section).split()[:170]),
            negative_prompt="; ".join(section for section in negative_sections if section).strip(),
            visual_preset=brief.visual_preset or template["default_visual_preset"],
            palette_tags=palette_tags,
            garment_tags=self._unique(garment_tags),
            style_tags=self._unique(style_tags),
            composition_tags=self._unique(composition_tags),
            metadata={
                "mode": brief.brief_mode,
                "style_identity": brief.style_identity,
                "style_family": brief.style_family,
                "brief_hash": brief.content_hash(),
                "knowledge_cards_count": len(brief.knowledge_cards),
                "knowledge_bundle_hash": brief.metadata.get("knowledge_bundle_hash"),
                "knowledge_query_hash": brief.metadata.get("knowledge_query_hash"),
                "retrieved_style_cards_count": brief.metadata.get("retrieved_style_cards_count"),
                "retrieved_color_cards_count": brief.metadata.get("retrieved_color_cards_count"),
                "retrieved_history_cards_count": brief.metadata.get("retrieved_history_cards_count"),
                "retrieved_tailoring_cards_count": brief.metadata.get("retrieved_tailoring_cards_count"),
                "retrieved_material_cards_count": brief.metadata.get("retrieved_material_cards_count"),
                "retrieved_flatlay_cards_count": brief.metadata.get("retrieved_flatlay_cards_count"),
                "diversity_constraints_hash": brief.metadata.get("diversity_constraints_hash"),
                "style_id": brief.metadata.get("style_id"),
                "source_style_id": brief.metadata.get("source_style_id"),
            },
        )
        compiled.metadata["compiled_prompt_hash"] = compiled.content_hash()
        return compiled

    def _profile_prompt_lines(self, brief: FashionBrief) -> list[str]:
        constraints = brief.profile_constraints if isinstance(brief.profile_constraints, dict) else {}
        lines: list[str] = []
        if brief.silhouette:
            lines.append(f"Silhouette direction: {brief.silhouette}.")
        mapping = (
            ("presentation_profile", "Presentation profile"),
            ("fit_preferences", "Fit preferences"),
            ("silhouette_preferences", "Silhouette preferences"),
            ("comfort_preferences", "Comfort preferences"),
            ("formality_preferences", "Formality preferences"),
            ("color_preferences", "Preferred colors"),
            ("preferred_items", "Preferred items"),
        )
        for key, label in mapping:
            value = constraints.get(key)
            rendered = self._render_profile_value(value)
            if rendered:
                lines.append(f"{label}: {rendered}.")
        return lines

    def _profile_negative_lines(self, brief: FashionBrief) -> list[str]:
        constraints = brief.profile_constraints if isinstance(brief.profile_constraints, dict) else {}
        lines: list[str] = []
        for key, label in (
            ("avoided_items", "avoid profile-conflicting items"),
            ("color_avoidances", "avoid profile-conflicting colors"),
        ):
            rendered = self._render_profile_value(constraints.get(key))
            if rendered:
                lines.append(f"{label}: {rendered}")
        return lines

    def _diversity_negative_lines(self, brief: FashionBrief) -> list[str]:
        constraints = brief.diversity_constraints
        if not isinstance(constraints, dict):
            return []
        lines: list[str] = []
        mapping = {
            "avoid_palette": "avoid previous palette",
            "avoid_hero_garments": "avoid previous hero garments",
            "avoid_silhouette_families": "avoid previous silhouette family",
            "avoid_composition_types": "avoid previous composition layout",
            "avoid_background_families": "avoid previous background family",
            "avoid_layout_density": "avoid previous layout density",
            "avoid_camera_distance": "avoid previous camera distance",
        }
        for key, label in mapping.items():
            values = constraints.get(key)
            if isinstance(values, list) and values:
                lines.append(f"{label}: {', '.join(str(value).strip() for value in values[:4] if str(value).strip())}")
        if constraints.get("force_visual_preset_shift"):
            lines.append("force visual preset shift from the recent generations")
        if constraints.get("force_material_contrast"):
            lines.append("force material contrast from the recent generations")
        if constraints.get("force_footwear_change"):
            lines.append("force footwear change from the recent generations")
        if constraints.get("force_accessory_change"):
            lines.append("force accessory change from the recent generations")
        return lines

    def _render_profile_value(self, value: object) -> str | None:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            if items:
                return ", ".join(items[:4])
        return None

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value).strip()
            lowered = cleaned.lower()
            if not cleaned or lowered in seen:
                continue
            seen.add(lowered)
            result.append(cleaned)
        return result
