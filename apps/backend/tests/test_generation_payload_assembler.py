import unittest

from app.application.visual_generation.contracts import WorkflowSelection
from app.application.visual_generation.services.generation_payload_assembler import GenerationPayloadAssembler
from app.domain.prompt_building.entities.compiled_image_prompt import CompiledImagePrompt
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.infrastructure.comfy.presets.visual_presets_registry import get_visual_preset


class GenerationPayloadAssemblerTests(unittest.IsolatedAsyncioTestCase):
    async def test_assembler_builds_visual_generation_plan_with_parser_traits(self) -> None:
        plan, metadata = await GenerationPayloadAssembler().assemble(
            fashion_brief=FashionBrief(
                style_identity="Soft Retro Prep",
                style_family="soft prep",
                brief_mode="style_exploration",
                garment_list=["oxford shirt", "pleated chinos"],
                palette=["camel", "cream"],
                materials=["cotton", "tweed"],
                composition_rules=["shift to textured surface"],
                diversity_constraints={"avoid_palette": ["chalk", "charcoal"]},
                metadata={
                    "style_id": "soft-retro-prep",
                    "knowledge_refs": [{"id": "style_catalog:soft-retro-prep"}],
                },
            ),
            compiled_prompt=CompiledImagePrompt(
                final_prompt="soft retro prep editorial flat lay",
                negative_prompt="avoid clutter",
                visual_preset="airy_catalog",
                palette_tags=["camel", "cream"],
                garment_tags=["oxford shirt", "pleated chinos"],
                metadata={},
            ),
            visual_preset=get_visual_preset("textured_surface"),
            workflow_selection=WorkflowSelection(
                workflow_name="style_exploration_variation",
                workflow_version="style_exploration_variation.json",
                template_path="app/infrastructure/comfy/workflows/style_exploration_variation.json",
            ),
        )

        self.assertEqual(plan.style_id, "soft-retro-prep")
        self.assertEqual(plan.workflow_name, "style_exploration_variation")
        self.assertEqual(plan.visual_preset_id, "textured_surface")
        self.assertEqual(plan.palette_tags, ["camel", "cream"])
        self.assertEqual(plan.garments_tags, ["oxford shirt", "pleated chinos"])
        self.assertEqual(plan.materials_tags, ["cotton", "tweed"])
        self.assertEqual(metadata.style_id, "soft-retro-prep")
        self.assertEqual(metadata.visual_preset_id, "textured_surface")
