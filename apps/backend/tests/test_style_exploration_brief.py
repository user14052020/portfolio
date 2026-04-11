import unittest

from app.application.stylist_chat.services.style_exploration_context_builder import StyleExplorationContextBuilder
from app.application.stylist_chat.use_cases.build_style_exploration_brief import BuildStyleExplorationBriefUseCase
from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints
from app.domain.style_exploration.entities.style_direction import StyleDirection


def make_style() -> StyleDirection:
    return StyleDirection(
        style_id="gallery-noir",
        style_name="Gallery Noir",
        style_family="art-led tailoring",
        palette=["forest", "ink", "bone"],
        silhouette_family="boxy layering",
        hero_garments=["field jacket", "pleated trousers"],
        footwear=["leather boots"],
        accessories=["scarf"],
        materials=["twill", "wool"],
        styling_mood=["quiet", "sharp"],
        composition_type="editorial flat lay",
        background_family="stone",
        layout_density="compact",
        camera_distance="tight overhead",
        visual_preset="editorial_studio",
    )


class StyleExplorationBriefTests(unittest.IsolatedAsyncioTestCase):
    async def test_brief_builder_produces_prompt_payload_with_hashes_and_shifted_visual_preset(self) -> None:
        use_case = BuildStyleExplorationBriefUseCase(
            context_builder=StyleExplorationContextBuilder(),
        )
        style_direction = make_style()
        constraints = DiversityConstraints(
            avoid_palette=["camel", "cream"],
            avoid_hero_garments=["oxford shirt"],
            avoid_composition_types=["editorial flat lay"],
            avoid_background_families=["paper"],
            force_visual_preset_shift=True,
            suggested_visual_preset="textured_surface",
            target_semantic_distance="high",
            target_visual_distance="high",
        )

        brief = await use_case.execute(
            style_direction=style_direction,
            history=[],
            diversity_constraints=constraints,
        )
        payload = brief.to_prompt_payload()

        self.assertEqual(brief.visual_preset, "textured_surface")
        self.assertEqual(brief.selected_style_direction.visual_preset, "textured_surface")
        self.assertIn("avoid palette: camel, cream", brief.negative_constraints)
        self.assertIn("shift to textured_surface visual preset", brief.composition_rules)
        self.assertEqual(payload["semantic_constraints_hash"], constraints.semantic_hash())
        self.assertEqual(payload["visual_constraints_hash"], constraints.visual_hash())
        self.assertEqual(payload["selected_style_direction"]["visual_preset"], "textured_surface")

