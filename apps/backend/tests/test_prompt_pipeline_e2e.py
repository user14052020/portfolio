import unittest

from app.application.prompt_building.services.prompt_pipeline_builder import PromptPipelineBuilder
from app.domain.prompt_building.entities.fashion_brief import FashionBrief


class PromptPipelineE2ETests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.builder = PromptPipelineBuilder()

    async def test_garment_matching_builds_anchor_centered_brief_and_compiled_prompt(self) -> None:
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

        self.assertEqual(preview["fashion_brief"].brief_mode, "garment_matching")
        self.assertIn("anchor garment centrality high", preview["fashion_brief"].composition_rules)
        self.assertIn("black leather jacket", preview["compiled_prompt"].final_prompt)

    async def test_occasion_outfit_carries_slot_logic_into_final_prompt(self) -> None:
        preview = await self.builder.preview_pipeline(
            brief={
                "mode": "occasion_outfit",
                "occasion_context": {"event_type": "exhibition", "dress_code": "smart casual", "color_preferences": ["olive"]},
                "structured_outfit_brief": {
                    "brief_type": "occasion_outfit",
                    "occasion_context": {"event_type": "exhibition", "dress_code": "smart casual", "color_preferences": ["olive"]},
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

        self.assertEqual(preview["fashion_brief"].brief_mode, "occasion_outfit")
        self.assertIn("event suitability first", preview["fashion_brief"].composition_rules)
        self.assertIn("exhibition", preview["compiled_prompt"].final_prompt)

    async def test_style_exploration_propagates_history_and_diversity_constraints(self) -> None:
        preview = await self.builder.preview_pipeline(
            brief={
                "mode": "style_exploration",
                "previous_style_directions": [{"style_id": "artful-minimalism", "palette": ["chalk", "charcoal"]}],
                "anti_repeat_constraints": {"avoid_palette": ["chalk", "charcoal"]},
                "structured_outfit_brief": {
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
                    "diversity_constraints": {"avoid_palette": ["chalk", "charcoal"], "force_visual_preset_shift": True},
                    "selected_style_direction": {"style_id": "soft-retro-prep", "style_name": "Soft Retro Prep"},
                    "visual_preset": "textured_surface",
                    "diversity_constraints_hash": "div-123",
                },
                "image_brief_en": "soft retro prep editorial flat lay",
                "recommendation_text": "Try a softer prep direction.",
            }
        )

        self.assertEqual(preview["fashion_brief"].metadata["previous_style_directions"][0]["style_id"], "artful-minimalism")
        self.assertEqual(preview["generation_payload"].metadata["anti_repeat_constraints"]["avoid_palette"], ["chalk", "charcoal"])
        self.assertEqual(preview["generation_payload"].metadata["diversity_constraints_hash"], "div-123")

    async def test_prompt_validation_catches_incomplete_briefs_before_generation(self) -> None:
        preview = await self.builder.preview_pipeline(
            brief={
                "mode": "garment_matching",
                "structured_outfit_brief": {
                    "brief_type": "garment_matching",
                    "anchor_summary": "",
                    "anchor_garment": {},
                    "tailoring_notes": [],
                    "color_logic": [],
                    "complementary_garments": [],
                },
                "image_brief_en": "",
                "recommendation_text": "",
            }
        )

        self.assertTrue(preview["validation_errors"])
        self.assertIsNone(preview["compiled_prompt"])
        self.assertIsNone(preview["generation_payload"])

    async def test_generation_payload_contains_required_metadata(self) -> None:
        preview = await self.builder.preview_pipeline(
            brief={
                "mode": "general_advice",
                "user_message": "Show me a cleaner outfit direction",
                "image_brief_en": "clean navy shirt and charcoal trousers outfit",
                "recommendation_text": "Keep it cleaner and sharper.",
                "knowledge_cards": [{"key": "general", "text": "Simplify the silhouette."}],
            }
        )

        metadata = preview["generation_payload"].metadata
        self.assertTrue(metadata["fashion_brief"])
        self.assertTrue(metadata["compiled_image_prompt"])
        self.assertTrue(metadata["workflow_name"])
        self.assertTrue(metadata["workflow_version"])
        self.assertIn("brief_hash", metadata)
        self.assertIn("compiled_prompt_hash", metadata)
