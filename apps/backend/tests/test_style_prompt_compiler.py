import unittest

from app.application.stylist_chat.services.style_prompt_compiler import StylePromptCompiler


class StylePromptCompilerTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_preserves_history_and_anti_repeat_constraints_in_generation_metadata(self) -> None:
        compiler = StylePromptCompiler()

        payload = await compiler.build(
            brief={
                "image_brief_en": "soft retro prep editorial flat lay",
                "recommendation_text": "Try a softer prep direction.",
                "asset_id": None,
                "previous_style_directions": [
                    {
                        "style_id": "artful-minimalism",
                        "style_name": "Artful Minimalism",
                        "palette": ["chalk", "charcoal"],
                    }
                ],
                "anti_repeat_constraints": {
                    "avoid_palette": ["chalk", "charcoal"],
                    "avoid_hero_garments": ["structured coat"],
                    "force_footwear_change": True,
                },
                "style_exploration_brief": {
                    "style_identity": "Soft Retro Prep",
                    "style_summary": "Soft Retro Prep; camel, cream; relaxed collegiate layering",
                    "palette": ["camel", "cream"],
                    "garment_list": ["oxford shirt", "pleated chinos"],
                    "materials": ["cotton"],
                    "footwear": ["loafers"],
                    "accessories": ["belt"],
                    "styling_notes": ["soft collegiate layering"],
                    "composition_rules": [
                        "use catalog grid",
                        "change the footwear family versus the recent history",
                        "shift to textured_surface visual preset",
                    ],
                    "negative_constraints": [
                        "avoid palette: chalk, charcoal",
                        "avoid footwear: derbies",
                    ],
                    "diversity_constraints": {
                        "target_semantic_distance": "high",
                        "target_visual_distance": "high",
                        "suggested_visual_preset": "textured_surface",
                    },
                    "selected_style_direction": {
                        "style_id": "soft-retro-prep",
                        "style_name": "Soft Retro Prep",
                        "visual_preset": "textured_surface",
                    },
                    "visual_preset": "textured_surface",
                    "composition_type": "catalog grid",
                    "background_family": "paper",
                    "semantic_constraints_hash": "abc123def456",
                    "visual_constraints_hash": "fed654cba321",
                    "diversity_constraints_hash": "aaa111bbb222",
                },
            }
        )

        self.assertEqual(payload["visual_preset"], "textured_surface")
        self.assertIn("Soft Retro Prep", payload["prompt"])
        self.assertIn("Styling notes: soft collegiate layering", payload["prompt"])
        self.assertEqual(payload["negative_prompt"], "avoid palette: chalk, charcoal; avoid footwear: derbies")
        self.assertEqual(
            payload["metadata"]["previous_style_directions"][0]["style_id"],
            "artful-minimalism",
        )
        self.assertEqual(
            payload["metadata"]["anti_repeat_constraints"]["avoid_palette"],
            ["chalk", "charcoal"],
        )
        self.assertEqual(payload["metadata"]["semantic_constraints_hash"], "abc123def456")
        self.assertEqual(payload["metadata"]["visual_constraints_hash"], "fed654cba321")
        self.assertEqual(payload["metadata"]["diversity_constraints_hash"], "aaa111bbb222")
