from typing import Any

from app.application.prompt_building.services.fashion_brief_builder import FashionBriefBuilder
from app.application.prompt_building.services.fashion_reasoning_service import (
    FashionReasoningInput,
    FashionReasoningService,
)
from app.application.prompt_building.services.generation_payload_builder import GenerationPayloadBuilder
from app.application.prompt_building.services.image_prompt_compiler import ImagePromptCompiler
from app.application.prompt_building.services.prompt_validator import PromptValidator
from app.application.prompt_building.use_cases.build_fashion_brief import BuildFashionBriefUseCase
from app.application.prompt_building.use_cases.compile_image_prompt import CompileImagePromptUseCase
from app.application.prompt_building.use_cases.validate_prompt_pipeline import ValidatePromptPipelineUseCase
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.infrastructure.comfy.comfy_generation_payload_adapter import ComfyGenerationPayloadAdapter


class PromptPipelineValidationError(RuntimeError):
    def __init__(self, *, errors: list[str]) -> None:
        super().__init__("Prompt pipeline validation failed")
        self.errors = errors


class PromptPipelineBuilder:
    def __init__(self) -> None:
        fashion_reasoning_service = FashionReasoningService(brief_builder=FashionBriefBuilder())
        self.build_fashion_brief = BuildFashionBriefUseCase(fashion_reasoning_service=fashion_reasoning_service)
        self.compile_image_prompt = CompileImagePromptUseCase(image_prompt_compiler=ImagePromptCompiler())
        self.validate_prompt_pipeline = ValidatePromptPipelineUseCase(prompt_validator=PromptValidator())
        self.generation_payload_builder = GenerationPayloadBuilder(
            payload_adapter=ComfyGenerationPayloadAdapter()
        )

    async def build(self, *, brief: dict[str, Any]) -> dict[str, Any]:
        preview = await self.preview_pipeline(brief=brief)
        validation_errors = preview["validation_errors"]
        if validation_errors:
            raise PromptPipelineValidationError(errors=validation_errors)
        generation_payload = preview["generation_payload"]
        return {
            "prompt": generation_payload.prompt,
            "negative_prompt": generation_payload.negative_prompt or None,
            "visual_preset": generation_payload.visual_preset,
            "image_brief_en": str(brief.get("image_brief_en") or ""),
            "recommendation_text": str(brief.get("recommendation_text") or ""),
            "input_asset_id": brief.get("asset_id"),
            "metadata": generation_payload.metadata,
            "visual_generation_plan": (
                generation_payload.visual_generation_plan.model_dump(mode="json")
                if generation_payload.visual_generation_plan is not None
                else None
            ),
            "generation_metadata": (
                generation_payload.generation_metadata.model_dump(mode="json")
                if generation_payload.generation_metadata is not None
                else None
            ),
        }

    async def preview_pipeline(self, *, brief: dict[str, Any]) -> dict[str, Any]:
        direct_fashion_brief = self._direct_fashion_brief(brief)
        if direct_fashion_brief is not None:
            fashion_brief = direct_fashion_brief
            validation_errors = await self.validate_prompt_pipeline.validate_brief(brief=fashion_brief)
            if validation_errors:
                return {
                    "fashion_brief": fashion_brief,
                    "compiled_prompt": None,
                    "generation_payload": None,
                    "validation_errors": validation_errors,
                }
            compiled_prompt = await self.compile_image_prompt.execute(brief=fashion_brief)
            validation_errors = await self.validate_prompt_pipeline.execute(
                brief=fashion_brief,
                compiled_prompt=compiled_prompt,
            )
            generation_payload = await self.generation_payload_builder.build(
                fashion_brief=fashion_brief,
                compiled_prompt=compiled_prompt,
                validation_errors=validation_errors,
            )
            return {
                "fashion_brief": fashion_brief,
                "compiled_prompt": compiled_prompt,
                "generation_payload": generation_payload,
                "validation_errors": validation_errors,
            }

        style_brief = brief.get("style_exploration_brief") if isinstance(brief.get("style_exploration_brief"), dict) else {}
        reasoning_input = FashionReasoningInput.model_validate(
            {
                "mode": brief.get("mode") or "general_advice",
                "user_message": brief.get("user_message"),
                "anchor_garment": (
                    brief.get("structured_outfit_brief", {}) or {}
                ).get("anchor_garment")
                if isinstance(brief.get("structured_outfit_brief"), dict)
                else None,
                "occasion_context": brief.get("occasion_context"),
                "style_direction": style_brief.get("selected_style_direction"),
                "style_history": brief.get("previous_style_directions") or [],
                "diversity_constraints": style_brief.get("diversity_constraints") or brief.get("anti_repeat_constraints") or {},
                "knowledge_cards": brief.get("knowledge_cards") or [],
                "knowledge_bundle": brief.get("knowledge_bundle"),
                "profile_context": brief.get("profile_context"),
                "visual_preset_candidates": [
                    value
                    for value in [
                        style_brief.get("visual_preset"),
                        brief.get("style_seed", {}).get("visual_preset")
                        if isinstance(brief.get("style_seed"), dict)
                        else None,
                    ]
                    if value
                ],
                "structured_outfit_brief": brief.get("structured_outfit_brief"),
                "recommendation_text": brief.get("recommendation_text"),
                "image_brief_en": brief.get("image_brief_en"),
                "style_seed": brief.get("style_seed"),
                "previous_style_directions": brief.get("previous_style_directions") or [],
                "anti_repeat_constraints": brief.get("anti_repeat_constraints") or {},
                "session_id": brief.get("session_id"),
                "message_id": brief.get("message_id"),
                "knowledge_provider_used": brief.get("knowledge_provider_used"),
            }
        )
        fashion_brief = await self.build_fashion_brief.execute(reasoning_input=reasoning_input)
        validation_errors = await self.validate_prompt_pipeline.validate_brief(brief=fashion_brief)
        if validation_errors:
            return {
                "fashion_brief": fashion_brief,
                "compiled_prompt": None,
                "generation_payload": None,
                "validation_errors": validation_errors,
            }
        compiled_prompt = await self.compile_image_prompt.execute(brief=fashion_brief)
        validation_errors = await self.validate_prompt_pipeline.execute(
            brief=fashion_brief,
            compiled_prompt=compiled_prompt,
        )
        generation_payload = await self.generation_payload_builder.build(
            fashion_brief=fashion_brief,
            compiled_prompt=compiled_prompt,
            validation_errors=validation_errors,
        )
        return {
            "fashion_brief": fashion_brief,
            "compiled_prompt": compiled_prompt,
            "generation_payload": generation_payload,
            "validation_errors": validation_errors,
        }

    def _direct_fashion_brief(self, brief: dict[str, Any]) -> FashionBrief | None:
        payload = brief.get("fashion_brief")
        if payload is None and _looks_like_fashion_brief(brief.get("structured_outfit_brief")):
            payload = brief.get("structured_outfit_brief")
        if not isinstance(payload, dict):
            return None
        return FashionBrief.model_validate(payload)


def _looks_like_fashion_brief(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(key in value for key in ("brief_mode", "style_identity", "style_direction")) and any(
        key in value for key in ("garment_list", "hero_garments", "palette", "composition_rules")
    )
