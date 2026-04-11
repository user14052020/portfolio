from app.domain.prompt_building.entities.compiled_image_prompt import CompiledImagePrompt
from app.domain.prompt_building.entities.fashion_brief import FashionBrief


class PromptValidator:
    async def validate_brief(self, brief: FashionBrief) -> list[str]:
        errors: list[str] = []
        if not brief.style_identity.strip():
            errors.append("style_identity is required")
        if brief.brief_mode != "general_advice" and not brief.garment_list:
            errors.append("garment_list is required for generation-oriented modes")
        if brief.brief_mode in {"garment_matching", "occasion_outfit", "style_exploration"} and not brief.tailoring_logic:
            errors.append("tailoring_logic is required for the selected mode")
        if brief.brief_mode in {"garment_matching", "occasion_outfit", "style_exploration"} and not brief.color_logic:
            errors.append("color_logic is required for the selected mode")
        if brief.brief_mode == "style_exploration" and not brief.diversity_constraints:
            errors.append("diversity_constraints are required for style_exploration")
        return errors

    async def validate_compiled(self, prompt: CompiledImagePrompt) -> list[str]:
        errors: list[str] = []
        if not prompt.final_prompt.strip():
            errors.append("final_prompt must not be empty")
        if not prompt.negative_prompt.strip():
            errors.append("negative_prompt must not be empty")
        if not prompt.visual_preset:
            errors.append("visual_preset is required")
        if not prompt.metadata.get("brief_hash"):
            errors.append("brief_hash is required for observability")
        if not prompt.metadata.get("compiled_prompt_hash"):
            errors.append("compiled_prompt_hash is required for observability")
        return errors
