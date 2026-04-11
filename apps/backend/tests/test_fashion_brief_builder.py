import unittest

from app.application.prompt_building.services.fashion_brief_builder import FashionBriefBuilder
from app.application.prompt_building.services.fashion_reasoning_service import FashionReasoningInput


class FashionBriefBuilderTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_style_exploration_brief_preserves_diversity_and_knowledge(self) -> None:
        builder = FashionBriefBuilder()

        brief = await builder.build(
            reasoning_input=FashionReasoningInput(
                mode="style_exploration",
                knowledge_cards=[
                    {"key": "diversity", "text": "Shift palette and silhouette together."},
                    {"key": "clarity", "text": "Keep one clear visual anchor."},
                ],
                structured_outfit_brief={
                    "brief_type": "style_exploration",
                    "style_identity": "Soft Retro Prep",
                    "style_family": "soft prep",
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
                },
                previous_style_directions=[{"style_id": "artful-minimalism"}],
                anti_repeat_constraints={"avoid_palette": ["chalk", "charcoal"]},
            )
        )

        self.assertEqual(brief.style_identity, "Soft Retro Prep")
        self.assertEqual(brief.brief_mode, "style_exploration")
        self.assertEqual(brief.diversity_constraints["avoid_palette"], ["chalk", "charcoal"])
        self.assertEqual(brief.metadata["previous_style_directions"][0]["style_id"], "artful-minimalism")
        self.assertIn("Shift palette and silhouette together.", brief.historical_reference)

    async def test_build_garment_matching_brief_centers_anchor_garment(self) -> None:
        builder = FashionBriefBuilder()

        brief = await builder.build(
            reasoning_input=FashionReasoningInput(
                mode="garment_matching",
                structured_outfit_brief={
                    "brief_type": "garment_matching",
                    "anchor_summary": "black leather jacket",
                    "anchor_garment": {
                        "garment_type": "jacket",
                        "category": "outerwear",
                        "color_primary": "black",
                        "material": "leather",
                    },
                    "tailoring_notes": ["keep the proportions clean"],
                    "color_logic": ["keep black as the anchor"],
                    "complementary_garments": ["clean knit", "straight trousers"],
                    "footwear_options": ["minimal boots"],
                    "accessories": ["structured belt"],
                    "image_prompt_notes": ["one coherent outfit only"],
                    "negative_constraints": ["do not overpower the anchor garment"],
                },
            )
        )

        self.assertEqual(brief.brief_mode, "garment_matching")
        self.assertEqual(brief.anchor_garment["garment_type"], "jacket")
        self.assertIn("anchor garment centrality high", brief.composition_rules)
        self.assertIn("black", brief.palette)
        self.assertIn("jacket", brief.garment_list)
