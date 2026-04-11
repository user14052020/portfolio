import unittest

from app.application.prompt_building.services.fashion_brief_builder import FashionBriefBuilder
from app.application.prompt_building.services.fashion_reasoning_service import (
    FashionReasoningInput,
    FashionReasoningService,
)
from app.application.prompt_building.services.generation_payload_builder import GenerationPayloadBuilder
from app.application.prompt_building.services.image_prompt_compiler import ImagePromptCompiler
from app.application.prompt_building.services.prompt_validator import PromptValidator
from app.infrastructure.comfy.comfy_generation_payload_adapter import ComfyGenerationPayloadAdapter


class PromptPipelineIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_reasoning_input_to_payload_preserves_style_exploration_constraints(self) -> None:
        reasoning_service = FashionReasoningService(brief_builder=FashionBriefBuilder())
        compiler = ImagePromptCompiler()
        validator = PromptValidator()
        payload_builder = GenerationPayloadBuilder(payload_adapter=ComfyGenerationPayloadAdapter())

        brief = await reasoning_service.build_brief(
            reasoning_input=FashionReasoningInput(
                mode="style_exploration",
                knowledge_cards=[{"key": "diversity", "text": "Shift palette and silhouette together."}],
                previous_style_directions=[{"style_id": "artful-minimalism"}],
                anti_repeat_constraints={"avoid_palette": ["chalk", "charcoal"]},
                structured_outfit_brief={
                    "brief_type": "style_exploration",
                    "style_identity": "Soft Retro Prep",
                    "tailoring_logic": ["relaxed collegiate layering"],
                    "color_logic": ["keep camel and cream calm"],
                    "garment_list": ["oxford shirt", "pleated chinos"],
                    "palette": ["camel", "cream"],
                    "materials": ["cotton"],
                    "footwear": ["loafers"],
                    "accessories": ["belt"],
                    "styling_notes": ["soft, warm, collegiate"],
                    "composition_rules": ["shift to textured surface"],
                    "negative_constraints": ["avoid palette: chalk, charcoal"],
                    "diversity_constraints": {"avoid_palette": ["chalk", "charcoal"]},
                    "selected_style_direction": {"style_id": "soft-retro-prep", "style_name": "Soft Retro Prep"},
                    "visual_preset": "textured_surface",
                    "diversity_constraints_hash": "div-123",
                },
            )
        )
        compiled = await compiler.compile(brief=brief)
        validation_errors = [
            *(await validator.validate_brief(brief)),
            *(await validator.validate_compiled(compiled)),
        ]
        payload = await payload_builder.build(
            fashion_brief=brief,
            compiled_prompt=compiled,
            validation_errors=validation_errors,
        )

        self.assertEqual(validation_errors, [])
        self.assertEqual(payload.metadata["anti_repeat_constraints"]["avoid_palette"], ["chalk", "charcoal"])
        self.assertEqual(payload.metadata["previous_style_directions"][0]["style_id"], "artful-minimalism")
        self.assertEqual(payload.metadata["diversity_constraints_hash"], "div-123")
