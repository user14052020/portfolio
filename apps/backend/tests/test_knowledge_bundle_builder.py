import unittest

from app.application.knowledge.services.knowledge_bundle_builder import KnowledgeBundleBuilder
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType


class KnowledgeBundleBuilderTests(unittest.TestCase):
    def test_bundle_builder_populates_trace_and_counts(self) -> None:
        style_card = KnowledgeCard(
            id="style:1",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            title="Soft Retro Prep",
            summary="Warm prep style.",
            style_id="soft-retro-prep",
        )
        flatlay_card = KnowledgeCard(
            id="flatlay:1",
            knowledge_type=KnowledgeType.FLATLAY_PROMPT_PATTERNS,
            title="Flatlay",
            summary="Use breathing space.",
        )
        query = KnowledgeQuery(mode="style_exploration", style_id="soft-retro-prep", limit=4)

        bundle = KnowledgeBundleBuilder().build(
            query=query,
            style_cards=[style_card],
            color_cards=[],
            history_cards=[],
            tailoring_cards=[],
            materials_cards=[],
            flatlay_cards=[flatlay_card],
        )

        self.assertEqual(bundle.retrieval_trace["retrieved_style_cards_count"], 1)
        self.assertEqual(bundle.retrieval_trace["retrieved_flatlay_cards_count"], 1)
        self.assertTrue(bundle.retrieval_trace["knowledge_query_hash"])
        self.assertTrue(bundle.retrieval_trace["knowledge_bundle_hash"])
