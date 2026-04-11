from typing import Any


class StylePromptCompiler:
    async def build(self, *, brief: dict[str, Any]) -> dict[str, Any]:
        style_brief = brief.get("style_exploration_brief") or {}
        diversity_constraints = style_brief.get("diversity_constraints") or {}
        selected_style = style_brief.get("selected_style_direction") or {}
        palette = [str(item).strip() for item in style_brief.get("palette", []) if str(item).strip()]
        garments = [str(item).strip() for item in style_brief.get("garment_list", []) if str(item).strip()]
        materials = [str(item).strip() for item in style_brief.get("materials", []) if str(item).strip()]
        footwear = [str(item).strip() for item in style_brief.get("footwear", []) if str(item).strip()]
        accessories = [str(item).strip() for item in style_brief.get("accessories", []) if str(item).strip()]
        styling_notes = [str(item).strip() for item in style_brief.get("styling_notes", []) if str(item).strip()]
        composition_rules = [
            str(item).strip() for item in style_brief.get("composition_rules", []) if str(item).strip()
        ]
        negative_constraints = [
            str(item).strip() for item in style_brief.get("negative_constraints", []) if str(item).strip()
        ]
        style_name = str(style_brief.get("style_identity") or selected_style.get("style_name") or "Style Direction").strip()
        style_summary = str(style_brief.get("style_summary") or style_name).strip()
        visual_preset = str(
            style_brief.get("visual_preset")
            or diversity_constraints.get("suggested_visual_preset")
            or selected_style.get("visual_preset")
            or "editorial_studio"
        ).strip()
        composition_type = str(
            style_brief.get("composition_type") or selected_style.get("composition_type") or "editorial flat lay"
        ).strip()
        background_family = str(
            style_brief.get("background_family") or selected_style.get("background_family") or "studio"
        ).strip()
        prompt_bits = [
            style_name,
            style_summary,
            f"Palette: {', '.join(palette[:4])}" if palette else "",
            f"Garments: {', '.join(garments[:4])}" if garments else "",
            f"Materials: {', '.join(materials[:3])}" if materials else "",
            f"Footwear: {', '.join(footwear[:2])}" if footwear else "",
            f"Accessories: {', '.join(accessories[:2])}" if accessories else "",
            f"Styling notes: {', '.join(styling_notes[:3])}" if styling_notes else "",
            f"Visual preset: {visual_preset}",
            f"Composition: {composition_type} on {background_family}",
            "; ".join(composition_rules[:3]),
        ]
        prompt = " ".join(bit for bit in prompt_bits if bit).strip()
        negative_prompt = "; ".join(negative_constraints[:5]) if negative_constraints else ""
        return {
            "prompt": " ".join(prompt.split()[:120]),
            "negative_prompt": negative_prompt or None,
            "visual_preset": visual_preset,
            "image_brief_en": str(brief.get("image_brief_en") or style_summary or style_name),
            "recommendation_text": str(brief.get("recommendation_text") or ""),
            "input_asset_id": brief.get("asset_id"),
            "metadata": {
                "style_direction_id": selected_style.get("style_id"),
                "source_style_id": selected_style.get("style_id"),
                "style_name": selected_style.get("style_name") or style_name,
                "palette": palette,
                "garment_tags": garments,
                "materials": materials,
                "footwear": footwear,
                "accessories": accessories,
                "visual_preset": visual_preset,
                "composition_type": composition_type,
                "background_family": background_family,
                "semantic_constraints_hash": style_brief.get("semantic_constraints_hash"),
                "visual_constraints_hash": style_brief.get("visual_constraints_hash"),
                "diversity_constraints_hash": style_brief.get("diversity_constraints_hash")
                or style_brief.get("semantic_constraints_hash")
                or style_brief.get("visual_constraints_hash"),
                "diversity_tags": {
                    "semantic": diversity_constraints.get("target_semantic_distance"),
                    "visual": diversity_constraints.get("target_visual_distance"),
                },
                "previous_style_directions": brief.get("previous_style_directions") or [],
                "anti_repeat_constraints": brief.get("anti_repeat_constraints") or {},
            },
        }
