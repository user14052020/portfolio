import unittest

from app.application.prompt_building.services.prompt_pipeline_builder import PromptPipelineBuilder
from app.domain.knowledge.entities import KnowledgeBundle, KnowledgeCard
from app.domain.knowledge.enums import KnowledgeType


class KnowledgePromptIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_prompt_builder_receives_non_empty_bundle_and_maps_it_into_brief(self) -> None:
        bundle = KnowledgeBundle(
            style_cards=[
                KnowledgeCard(
                    id="style:soft-retro-prep",
                    knowledge_type=KnowledgeType.STYLE_CATALOG,
                    title="Soft Retro Prep",
                    summary="Warm collegiate style direction.",
                    style_id="soft-retro-prep",
                    metadata={
                        "palette": ["camel", "cream"],
                        "hero_garments": ["oxford shirt", "pleated chinos"],
                        "materials": ["cotton"],
                        "silhouette_family": "relaxed collegiate layering",
                        "negative_constraints": ["avoid neon"],
                    },
                )
            ],
            color_cards=[
                KnowledgeCard(
                    id="color:soft-retro-prep",
                    knowledge_type=KnowledgeType.COLOR_THEORY,
                    title="Color logic",
                    summary="Keep camel and cream calm.",
                    style_id="soft-retro-prep",
                )
            ],
            history_cards=[
                KnowledgeCard(
                    id="history:soft-retro-prep",
                    knowledge_type=KnowledgeType.FASHION_HISTORY,
                    title="History",
                    summary="Rooted in collegiate heritage.",
                    style_id="soft-retro-prep",
                )
            ],
            tailoring_cards=[
                KnowledgeCard(
                    id="tailoring:soft-retro-prep",
                    knowledge_type=KnowledgeType.TAILORING_PRINCIPLES,
                    title="Tailoring",
                    summary="Keep one relaxed and one cleaner line.",
                    style_id="soft-retro-prep",
                )
            ],
            materials_cards=[
                KnowledgeCard(
                    id="materials:soft-retro-prep",
                    knowledge_type=KnowledgeType.MATERIALS_FABRICS,
                    title="Materials",
                    summary="Use cotton and tweed.",
                    style_id="soft-retro-prep",
                    metadata={"materials": ["cotton", "tweed"]},
                )
            ],
            flatlay_cards=[
                KnowledgeCard(
                    id="flatlay:soft-retro-prep",
                    knowledge_type=KnowledgeType.FLATLAY_PROMPT_PATTERNS,
                    title="Flatlay",
                    summary="Use breathing space between garments.",
                    style_id="soft-retro-prep",
                )
            ],
            retrieval_trace={
                "knowledge_query_hash": "query-123",
                "knowledge_bundle_hash": "bundle-456",
                "retrieved_style_cards_count": 1,
                "retrieved_color_cards_count": 1,
                "retrieved_history_cards_count": 1,
                "retrieved_tailoring_cards_count": 1,
                "retrieved_material_cards_count": 1,
                "retrieved_flatlay_cards_count": 1,
            },
        )

        preview = await PromptPipelineBuilder().preview_pipeline(
            brief={
                "mode": "style_exploration",
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
                    "diversity_constraints": {"avoid_palette": ["chalk", "charcoal"]},
                    "selected_style_direction": {"style_id": "soft-retro-prep", "style_name": "Soft Retro Prep"},
                    "visual_preset": "airy_catalog",
                    "diversity_constraints_hash": "div-123",
                },
                "knowledge_bundle": bundle.model_dump(mode="json"),
                "knowledge_cards": [],
                "image_brief_en": "soft retro prep editorial flat lay",
                "recommendation_text": "Try a softer prep direction.",
                "previous_style_directions": [{"style_id": "artful-minimalism"}],
                "anti_repeat_constraints": {"avoid_palette": ["chalk", "charcoal"]},
            }
        )

        fashion_brief = preview["fashion_brief"]
        payload_metadata = preview["generation_payload"].metadata
        self.assertIn("Rooted in collegiate heritage.", fashion_brief.historical_reference)
        self.assertIn("Keep one relaxed and one cleaner line.", fashion_brief.tailoring_logic)
        self.assertIn("Keep camel and cream calm.", fashion_brief.color_logic)
        self.assertIn("cotton", fashion_brief.materials)
        self.assertIn("Use breathing space between garments.", fashion_brief.composition_rules)
        self.assertEqual(payload_metadata["knowledge_bundle_hash"], "bundle-456")
        self.assertEqual(payload_metadata["retrieved_style_cards_count"], 1)
