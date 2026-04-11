import unittest

from app.application.visual_generation.services.workflow_selector import ComfyWorkflowSelector
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.infrastructure.comfy.presets.visual_presets_registry import get_visual_preset


class WorkflowSelectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_garment_matching_selects_anchor_workflow(self) -> None:
        selection = await ComfyWorkflowSelector().select(
            mode="garment_matching",
            visual_preset=get_visual_preset("editorial_studio"),
            fashion_brief=FashionBrief(style_identity="Jacket", brief_mode="garment_matching"),
        )

        self.assertEqual(selection.workflow_name, "garment_matching_variation")

    async def test_style_exploration_selects_diversity_workflow(self) -> None:
        selection = await ComfyWorkflowSelector().select(
            mode="style_exploration",
            visual_preset=get_visual_preset("dark_gallery"),
            fashion_brief=FashionBrief(style_identity="Style", brief_mode="style_exploration"),
        )

        self.assertEqual(selection.workflow_name, "style_exploration_variation")

    async def test_occasion_selects_practical_workflow(self) -> None:
        selection = await ComfyWorkflowSelector().select(
            mode="occasion_outfit",
            visual_preset=get_visual_preset("practical_board"),
            fashion_brief=FashionBrief(style_identity="Occasion", brief_mode="occasion_outfit"),
        )

        self.assertEqual(selection.workflow_name, "occasion_outfit_variation")
