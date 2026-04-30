import unittest

from app.application.prompt_building.services.fashion_brief_builder import FashionBriefBuilder
from app.application.prompt_building.services.fashion_reasoning_service import FashionReasoningInput
from app.domain.knowledge.entities import KnowledgeBundle, KnowledgeCard
from app.domain.knowledge.enums import KnowledgeType
from app.domain.reasoning import ProfileContextSnapshot


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

    async def test_build_general_advice_brief_injects_enriched_style_metadata_from_knowledge_bundle(self) -> None:
        builder = FashionBriefBuilder()
        bundle = KnowledgeBundle(
            style_cards=[
                KnowledgeCard(
                    id="style_catalog:soft-retro-prep",
                    knowledge_type=KnowledgeType.STYLE_CATALOG,
                    title="Soft Retro Prep",
                    summary="Soft collegiate style with warmth.",
                    style_id="soft-retro-prep",
                    metadata={
                        "canonical_name": "soft retro prep",
                        "palette": ["camel", "cream"],
                        "hero_garments": ["camel blazer"],
                        "secondary_garments": ["pleated chinos"],
                        "materials": ["cotton", "tweed"],
                        "shoes": ["loafers"],
                        "core_accessories": ["belt"],
                        "core_style_logic": ["Blend prep structure with softer warmth."],
                        "styling_rules": ["Keep the palette edited and relaxed."],
                        "casual_adaptations": ["Swap stiff shirting for softer knit layers."],
                        "historical_notes": ["References collegiate heritage."],
                        "overlap_context": ["Sits between prep and soft retro casual."],
                        "signature_details": ["soft blazer shoulder"],
                        "visual_motifs": ["relaxed layering"],
                        "lighting_mood": ["soft daylight"],
                        "photo_treatment": ["editorial grain"],
                        "composition_cues": ["leave breathing room between garments"],
                        "negative_guidance": ["Avoid neon accents."],
                    },
                )
            ]
        )

        brief = await builder.build(
            reasoning_input=FashionReasoningInput(
                mode="general_advice",
                recommendation_text="Let's build a warm retro-prep outfit.",
                knowledge_bundle=bundle.model_dump(mode="json"),
            )
        )

        self.assertEqual(brief.style_identity, "Let's build a warm retro-prep outfit")
        self.assertIn("camel", brief.palette)
        self.assertIn("camel blazer", brief.garment_list)
        self.assertIn("cotton", brief.materials)
        self.assertIn("loafers", brief.footwear)
        self.assertIn("belt", brief.accessories)
        self.assertIn("soft blazer shoulder", brief.styling_notes)
        self.assertIn("References collegiate heritage.", brief.historical_reference)
        self.assertIn("Blend prep structure with softer warmth.", brief.tailoring_logic)
        self.assertIn("leave breathing room between garments", brief.composition_rules)
        self.assertIn("Avoid neon accents.", brief.negative_constraints)

    async def test_build_brief_carries_normalized_profile_constraints_for_generation_handoff(self) -> None:
        builder = FashionBriefBuilder()

        brief = await builder.build(
            reasoning_input=FashionReasoningInput(
                mode="style_exploration",
                structured_outfit_brief={
                    "brief_type": "style_exploration",
                    "style_identity": "Structured Soft Prep",
                    "garment_list": ["blazer", "trousers"],
                    "palette": ["navy"],
                    "composition_rules": ["keep the layout clean"],
                    "selected_style_direction": {
                        "style_id": "structured-soft-prep",
                        "style_name": "Structured Soft Prep",
                    },
                },
                profile_context_snapshot=ProfileContextSnapshot(
                    presentation_profile="androgynous",
                    fit_preferences=("relaxed",),
                    silhouette_preferences=("structured",),
                    avoided_items=("heels",),
                    legacy_values={"height_cm": 175},
                    source="profile_context_service",
                ),
            )
        )

        self.assertEqual(brief.profile_constraints["presentation_profile"], "androgynous")
        self.assertEqual(brief.profile_constraints["fit_preferences"], ["relaxed"])
        self.assertEqual(brief.profile_constraints["avoided_items"], ["heels"])
        self.assertEqual(brief.profile_context_snapshot["source"], "profile_context_service")
        self.assertEqual(brief.profile_context_snapshot["values"]["height_cm"], 175)
