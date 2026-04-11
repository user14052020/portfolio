import unittest

from app.application.prompt_building.services.prompt_pipeline_builder import PromptPipelineBuilder


class VisualGenerationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.builder = PromptPipelineBuilder()

    async def test_garment_matching_builds_anchor_centric_visual_plan(self) -> None:
        preview = await self.builder.preview_pipeline(
            brief={
                "mode": "garment_matching",
                "structured_outfit_brief": {
                    "brief_type": "garment_matching",
                    "anchor_summary": "black leather jacket",
                    "anchor_garment": {"garment_type": "jacket", "color_primary": "black", "material": "leather"},
                    "tailoring_notes": ["keep the proportions clean"],
                    "color_logic": ["keep black as the anchor"],
                    "complementary_garments": ["clean knit", "straight trousers"],
                    "footwear_options": ["minimal boots"],
                    "accessories": ["structured belt"],
                    "image_prompt_notes": ["one coherent outfit only"],
                    "negative_constraints": ["do not overpower the anchor garment"],
                },
                "image_brief_en": "black leather jacket outfit",
                "recommendation_text": "A clean outfit around the jacket.",
            }
        )

        plan = preview["generation_payload"].visual_generation_plan
        metadata = preview["generation_payload"].generation_metadata
        assert plan is not None
        assert metadata is not None
        self.assertEqual(plan.anchor_garment_centrality, "high")
        self.assertEqual(plan.layout_archetype, "centered anchor composition")
        self.assertEqual(plan.workflow_name, "garment_matching_variation")
        self.assertEqual(metadata.visual_preset_id, plan.visual_preset_id)

    async def test_style_exploration_pushes_parser_traits_and_anti_repeat_into_visual_layer(self) -> None:
        preview = await self.builder.preview_pipeline(
            brief={
                "mode": "style_exploration",
                "previous_style_directions": [{"visual_preset": "textured_surface"}],
                "anti_repeat_constraints": {
                    "force_visual_preset_shift": True,
                    "avoid_background_families": ["warm wood"],
                    "avoid_camera_distance": ["wider editorial overhead"],
                },
                "structured_outfit_brief": {
                    "brief_type": "style_exploration",
                    "style_identity": "Soft Retro Prep",
                    "tailoring_logic": ["relaxed collegiate layering"],
                    "color_logic": ["keep camel and cream calm"],
                    "garment_list": ["oxford shirt", "pleated chinos"],
                    "palette": ["camel", "cream"],
                    "materials": ["cotton", "tweed"],
                    "footwear": ["loafers"],
                    "accessories": ["belt"],
                    "styling_notes": ["soft, warm, collegiate"],
                    "composition_rules": ["shift to textured surface"],
                    "negative_constraints": ["avoid palette: chalk, charcoal"],
                    "diversity_constraints": {
                        "force_visual_preset_shift": True,
                        "avoid_background_families": ["warm wood"],
                        "avoid_camera_distance": ["wider editorial overhead"],
                    },
                    "selected_style_direction": {"style_id": "soft-retro-prep", "style_name": "Soft Retro Prep"},
                    "visual_preset": "textured_surface",
                },
                "image_brief_en": "soft retro prep editorial flat lay",
                "recommendation_text": "Try a softer prep direction.",
            }
        )

        plan = preview["generation_payload"].visual_generation_plan
        metadata = preview["generation_payload"].generation_metadata
        assert plan is not None
        assert metadata is not None
        self.assertEqual(plan.style_id, "soft-retro-prep")
        self.assertNotEqual(plan.visual_preset_id, "textured_surface")
        self.assertNotEqual(plan.background_family, "warm wood")
        self.assertNotEqual(plan.camera_distance, "wider editorial overhead")
        self.assertEqual(plan.materials_tags, ["cotton", "tweed"])
        self.assertTrue(plan.diversity_profile["force_visual_preset_shift"])
        self.assertTrue(metadata.diversity_constraints["force_visual_preset_shift"])

    async def test_occasion_outfit_builds_practical_visual_plan(self) -> None:
        preview = await self.builder.preview_pipeline(
            brief={
                "mode": "occasion_outfit",
                "occasion_context": {
                    "event_type": "exhibition",
                    "dress_code": "smart casual",
                    "color_preferences": ["olive"],
                },
                "structured_outfit_brief": {
                    "brief_type": "occasion_outfit",
                    "occasion_context": {
                        "event_type": "exhibition",
                        "dress_code": "smart casual",
                        "color_preferences": ["olive"],
                    },
                    "tailoring_notes": ["keep the silhouette polished"],
                    "silhouette_logic": ["quietly elongated silhouette"],
                    "color_logic": ["olive should stay refined"],
                    "garment_recommendations": ["clean overshirt", "wide trousers"],
                    "footwear_recommendations": ["minimal derby shoes"],
                    "accessories": ["compact bag"],
                    "impression_logic": ["thoughtful and a little bold"],
                    "image_prompt_notes": ["one complete event-aware outfit only"],
                    "negative_constraints": ["do not underdress the event"],
                },
                "image_brief_en": "gallery-ready outfit",
                "recommendation_text": "A thoughtful exhibition outfit.",
            }
        )

        plan = preview["generation_payload"].visual_generation_plan
        metadata = preview["generation_payload"].generation_metadata
        assert plan is not None
        assert metadata is not None
        self.assertEqual(plan.practical_coherence, "high")
        self.assertEqual(plan.layout_archetype, "practical dressing board")
        self.assertEqual(plan.workflow_name, "occasion_outfit_variation")
        self.assertEqual(metadata.practical_coherence, "high")
