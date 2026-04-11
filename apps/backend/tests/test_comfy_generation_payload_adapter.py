import unittest

from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan
from app.infrastructure.comfy.comfy_generation_payload_adapter import ComfyGenerationPayloadAdapter


class ComfyGenerationPayloadAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_adapter_produces_backend_specific_payload_without_leaking_into_domain(self) -> None:
        adapter = ComfyGenerationPayloadAdapter()
        plan = VisualGenerationPlan(
            mode="style_exploration",
            style_id="soft-retro-prep",
            style_name="Soft Retro Prep",
            fashion_brief_hash="brief-123",
            compiled_prompt_hash="compiled-456",
            final_prompt="editorial outfit",
            negative_prompt="no clutter",
            visual_preset_id="editorial_studio",
            workflow_name="style_exploration_variation",
            workflow_version="style_exploration_variation.json",
            layout_archetype="diagonal editorial spread",
            background_family="warm wood",
            metadata={"brief_hash": "brief-123"},
        )
        metadata = GenerationMetadata(
            mode="style_exploration",
            style_id="soft-retro-prep",
            style_name="Soft Retro Prep",
            fashion_brief_hash="brief-123",
            compiled_prompt_hash="compiled-456",
            final_prompt="editorial outfit",
            negative_prompt="no clutter",
            workflow_name="style_exploration_variation",
            workflow_version="style_exploration_variation.json",
            visual_preset_id="editorial_studio",
            background_family="warm wood",
            layout_archetype="diagonal editorial spread",
        )

        payload = await adapter.adapt(plan=plan, metadata=metadata)

        self.assertEqual(payload.workflow_name, "style_exploration_variation")
        self.assertEqual(payload.workflow_version, "style_exploration_variation.json")
        self.assertEqual(payload.prompt, "editorial outfit")
        self.assertEqual(payload.negative_prompt, "no clutter")
        self.assertEqual(payload.metadata["brief_hash"], "brief-123")
        assert payload.visual_generation_plan is not None
        assert payload.generation_metadata is not None
        self.assertEqual(payload.visual_generation_plan.visual_preset_id, "editorial_studio")
        self.assertEqual(payload.generation_metadata.visual_preset_id, "editorial_studio")
