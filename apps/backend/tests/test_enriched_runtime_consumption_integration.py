import unittest

from app.application.prompt_building.services.prompt_pipeline_builder import PromptPipelineBuilder
from app.domain.knowledge.entities import KnowledgeBundle, KnowledgeCard
from app.domain.knowledge.enums import KnowledgeType


class EnrichedRuntimeConsumptionIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_consultation_uses_enriched_style_knowledge(self) -> None:
        preview = await PromptPipelineBuilder().preview_pipeline(
            brief=self._build_pipeline_brief(),
        )

        fashion_brief = preview["fashion_brief"]

        self.assertIn("Blend collegiate structure with softened warmth.", fashion_brief.tailoring_logic)
        self.assertIn("Keep prep elements edited and breathable.", fashion_brief.tailoring_logic)
        self.assertIn(
            "References collegiate heritage with a softer, modern filter.",
            fashion_brief.historical_reference,
        )
        self.assertIn("Bridges prep and retro casual dressing.", fashion_brief.historical_reference)
        self.assertIn("Avoid neon accents.", fashion_brief.negative_constraints)
        self.assertEqual(
            fashion_brief.metadata["presentation_short_explanation"],
            "Soft Retro Prep reframes collegiate dressing through warmer colors and softer structure.",
        )
        self.assertEqual(
            fashion_brief.metadata["what_makes_it_distinct"],
            ["Warm prep palette", "Relaxed but polished layering"],
        )

    async def test_generation_uses_enriched_image_data(self) -> None:
        preview = await PromptPipelineBuilder().preview_pipeline(
            brief=self._build_pipeline_brief(),
        )

        compiled_prompt = preview["compiled_prompt"]
        generation_payload = preview["generation_payload"]
        metadata = generation_payload.metadata

        self.assertIn("camel blazer", compiled_prompt.garment_tags)
        self.assertIn("oxford shirt", compiled_prompt.garment_tags)
        self.assertIn("pleated chinos", compiled_prompt.garment_tags)
        self.assertIn("leave breathing room between garments", compiled_prompt.composition_tags)
        self.assertIn("avoid neon accents", compiled_prompt.negative_prompt.lower())
        self.assertEqual(metadata["garment_tags"][:3], ["camel blazer", "oxford shirt", "pleated chinos"])
        self.assertEqual(metadata["materials_tags"], ["cotton", "tweed"])
        self.assertEqual(
            metadata["generation_metadata"]["style_explanation_short"],
            "Soft Retro Prep reframes collegiate dressing through warmer colors and softer structure.",
        )
        self.assertEqual(
            metadata["generation_metadata"]["style_explanation_distinct_points"],
            ["Warm prep palette", "Relaxed but polished layering"],
        )

    async def test_product_style_consultation_is_richer_with_enriched_facets(self) -> None:
        preview = await PromptPipelineBuilder().preview_pipeline(
            brief=self._build_pipeline_brief(),
        )

        fashion_brief = preview["fashion_brief"]
        populated_product_facets = [
            fashion_brief.palette,
            fashion_brief.garment_list,
            fashion_brief.materials,
            fashion_brief.footwear,
            fashion_brief.accessories,
            fashion_brief.tailoring_logic,
            fashion_brief.historical_reference,
            fashion_brief.styling_notes,
            fashion_brief.composition_rules,
            fashion_brief.negative_constraints,
        ]

        self.assertGreaterEqual(sum(1 for facet in populated_product_facets if facet), 10)
        self.assertEqual(fashion_brief.style_identity, "Soft Retro Prep")
        self.assertEqual(fashion_brief.style_family, "soft retro prep")
        self.assertIn("camel", fashion_brief.palette)
        self.assertIn("navy", fashion_brief.palette)
        self.assertIn("camel blazer", fashion_brief.garment_list)
        self.assertIn("loafers", fashion_brief.footwear)
        self.assertIn("belt", fashion_brief.accessories)
        self.assertIn("softly structured blazer", fashion_brief.styling_notes)
        self.assertIn("soft daylight", fashion_brief.composition_rules)
        self.assertEqual(fashion_brief.metadata["retrieved_style_cards_count"], 1)

    async def test_product_generation_consistency_keeps_style_identity_across_outputs(self) -> None:
        built = await PromptPipelineBuilder().build(
            brief=self._build_pipeline_brief(),
        )

        metadata = built["metadata"]
        visual_plan = built["visual_generation_plan"]
        generation_metadata = built["generation_metadata"]

        self.assertEqual(built["prompt"], visual_plan["final_prompt"])
        self.assertEqual(built["prompt"], generation_metadata["final_prompt"])
        self.assertEqual(visual_plan["style_id"], "soft-retro-prep")
        self.assertEqual(generation_metadata["style_id"], "soft-retro-prep")
        self.assertEqual(metadata["style_id"], "soft-retro-prep")
        self.assertEqual(metadata["style_name"], "Soft Retro Prep")
        self.assertEqual(metadata["visual_preset"], visual_plan["visual_preset_id"])
        self.assertEqual(generation_metadata["visual_preset_id"], visual_plan["visual_preset_id"])
        self.assertEqual(metadata["palette_tags"], visual_plan["palette_tags"])
        self.assertEqual(generation_metadata["palette_tags"], visual_plan["palette_tags"])
        self.assertEqual(metadata["garment_tags"], visual_plan["garments_tags"])
        self.assertEqual(generation_metadata["garments_tags"], visual_plan["garments_tags"])
        self.assertEqual(metadata["knowledge_refs"], visual_plan["knowledge_refs"])
        self.assertEqual(generation_metadata["knowledge_refs"], visual_plan["knowledge_refs"])
        self.assertEqual(metadata["validation_errors_count"], 0)

    def _build_pipeline_brief(self) -> dict[str, object]:
        bundle = KnowledgeBundle(
            style_cards=[
                KnowledgeCard(
                    id="style_catalog:soft-retro-prep",
                    knowledge_type=KnowledgeType.STYLE_CATALOG,
                    title="Soft Retro Prep",
                    summary="A warmer and more relaxed collegiate style.",
                    style_id="soft-retro-prep",
                    metadata={
                        "canonical_name": "soft retro prep",
                        "palette": ["camel", "cream", "navy"],
                        "hero_garments": ["camel blazer", "oxford shirt"],
                        "secondary_garments": ["pleated chinos"],
                        "materials": ["cotton", "tweed"],
                        "shoes": ["loafers"],
                        "core_accessories": ["belt"],
                        "core_style_logic": ["Blend collegiate structure with softened warmth."],
                        "styling_rules": ["Keep prep elements edited and breathable."],
                        "casual_adaptations": ["Use softer knits instead of stiff layers."],
                        "historical_notes": ["References collegiate heritage with a softer, modern filter."],
                        "overlap_context": ["Bridges prep and retro casual dressing."],
                        "signature_details": ["softly structured blazer"],
                        "visual_motifs": ["relaxed layering"],
                        "lighting_mood": ["soft daylight"],
                        "photo_treatment": ["editorial grain"],
                        "composition_cues": ["leave breathing room between garments"],
                        "negative_guidance": ["Avoid neon accents."],
                        "presentation_short_explanation": (
                            "Soft Retro Prep reframes collegiate dressing through warmer colors and softer structure."
                        ),
                        "presentation_one_sentence_description": (
                            "A softened collegiate direction with warm neutrals and relaxed polish."
                        ),
                        "what_makes_it_distinct": ["Warm prep palette", "Relaxed but polished layering"],
                    },
                )
            ],
            retrieval_trace={
                "knowledge_query_hash": "query-soft-retro-prep",
                "knowledge_bundle_hash": "bundle-soft-retro-prep",
                "retrieved_style_cards_count": 1,
            },
        )
        return {
            "mode": "style_exploration",
            "structured_outfit_brief": {
                "brief_type": "style_exploration",
                "style_identity": "Soft Retro Prep",
                "tailoring_logic": [],
                "color_logic": [],
                "garment_list": [],
                "palette": [],
                "materials": [],
                "footwear": [],
                "accessories": [],
                "styling_notes": [],
                "composition_rules": [],
                "negative_constraints": [],
                "selected_style_direction": {
                    "style_id": "soft-retro-prep",
                    "style_name": "Soft Retro Prep",
                },
                "visual_preset": "airy_catalog",
            },
            "knowledge_bundle": bundle.model_dump(mode="json"),
            "knowledge_cards": [],
            "image_brief_en": "soft retro prep editorial flat lay",
            "recommendation_text": "Try a softer retro-prep direction.",
        }


if __name__ == "__main__":
    unittest.main()
