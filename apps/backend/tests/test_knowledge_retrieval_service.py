import unittest

from app.application.knowledge.services.knowledge_bundle_builder import KnowledgeBundleBuilder
from app.application.knowledge.services.knowledge_ranker import KnowledgeRanker
from app.application.knowledge.services.knowledge_retrieval_service import DefaultKnowledgeRetrievalService
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType


class FakeStyleCatalogRepository:
    def __init__(self, cards):
        self.cards = cards

    async def search(self, *, query):
        return list(self.cards)

    async def list_candidate_styles(self, *, limit, exclude_style_ids=None):
        return list(self.cards)[:limit]


class FakeDerivedRepository:
    def __init__(self, cards):
        self.cards = cards

    async def search(self, *, query, context_style_cards=None):
        return list(self.cards)


class KnowledgeRetrievalServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_style_exploration_retrieves_style_history_and_flatlay_groups(self) -> None:
        style_cards = [
            KnowledgeCard(
                id="style:soft-retro-prep",
                knowledge_type=KnowledgeType.STYLE_CATALOG,
                title="Soft Retro Prep",
                summary="Warm prep style.",
                style_id="soft-retro-prep",
                metadata={"palette": ["camel", "cream"], "hero_garments": ["oxford shirt"]},
            )
        ]
        history_cards = [
            KnowledgeCard(
                id="history:soft-retro-prep",
                knowledge_type=KnowledgeType.FASHION_HISTORY,
                title="History",
                summary="Collegiate heritage.",
                style_id="soft-retro-prep",
            )
        ]
        flatlay_cards = [
            KnowledgeCard(
                id="flatlay:soft-retro-prep",
                knowledge_type=KnowledgeType.FLATLAY_PROMPT_PATTERNS,
                title="Flatlay",
                summary="Use soft spacing.",
                style_id="soft-retro-prep",
            )
        ]
        service = DefaultKnowledgeRetrievalService(
            style_catalog_repository=FakeStyleCatalogRepository(style_cards),
            color_theory_repository=FakeDerivedRepository([]),
            fashion_history_repository=FakeDerivedRepository(history_cards),
            tailoring_principles_repository=FakeDerivedRepository([]),
            materials_fabrics_repository=FakeDerivedRepository([]),
            flatlay_patterns_repository=FakeDerivedRepository(flatlay_cards),
            knowledge_ranker=KnowledgeRanker(),
            knowledge_bundle_builder=KnowledgeBundleBuilder(),
        )

        bundle = await service.retrieve(
            KnowledgeQuery(mode="style_exploration", style_id="soft-retro-prep", limit=6)
        )

        self.assertEqual(len(bundle.style_cards), 1)
        self.assertEqual(len(bundle.history_cards), 1)
        self.assertEqual(len(bundle.flatlay_cards), 1)
        self.assertTrue(bundle.retrieval_trace["knowledge_bundle_hash"])

    async def test_garment_matching_retrieves_style_tailoring_and_material_cards(self) -> None:
        service = DefaultKnowledgeRetrievalService(
            style_catalog_repository=FakeStyleCatalogRepository(
                [
                    KnowledgeCard(
                        id="style:leather-minimal",
                        knowledge_type=KnowledgeType.STYLE_CATALOG,
                        title="Leather Minimalism",
                        summary="A clean leather-centered style.",
                        style_id="leather-minimal",
                        tags=["jacket", "leather", "black"],
                        metadata={"materials": ["leather"], "hero_garments": ["jacket"]},
                    )
                ]
            ),
            color_theory_repository=FakeDerivedRepository([]),
            fashion_history_repository=FakeDerivedRepository([]),
            tailoring_principles_repository=FakeDerivedRepository(
                [
                    KnowledgeCard(
                        id="tailoring:1",
                        knowledge_type=KnowledgeType.TAILORING_PRINCIPLES,
                        title="Tailoring",
                        summary="Balance the anchor with one clean base.",
                    )
                ]
            ),
            materials_fabrics_repository=FakeDerivedRepository(
                [
                    KnowledgeCard(
                        id="materials:1",
                        knowledge_type=KnowledgeType.MATERIALS_FABRICS,
                        title="Materials",
                        summary="Support leather with softer textures.",
                    )
                ]
            ),
            flatlay_patterns_repository=FakeDerivedRepository([]),
            knowledge_ranker=KnowledgeRanker(),
            knowledge_bundle_builder=KnowledgeBundleBuilder(),
        )

        bundle = await service.retrieve(
            KnowledgeQuery(
                mode="garment_matching",
                anchor_garment={"garment_type": "jacket", "material": "leather", "color_primary": "black"},
                limit=6,
            )
        )

        self.assertEqual(len(bundle.style_cards), 1)
        self.assertEqual(len(bundle.tailoring_cards), 1)
        self.assertEqual(len(bundle.materials_cards), 1)

    async def test_occasion_outfit_retrieves_occasion_relevant_style_color_and_tailoring(self) -> None:
        service = DefaultKnowledgeRetrievalService(
            style_catalog_repository=FakeStyleCatalogRepository(
                [
                    KnowledgeCard(
                        id="style:gallery-smart-casual",
                        knowledge_type=KnowledgeType.STYLE_CATALOG,
                        title="Gallery Smart Casual",
                        summary="Polished exhibition dressing.",
                        style_id="gallery-smart-casual",
                        tags=["exhibition", "smart casual", "olive"],
                        metadata={"occasion_fit": ["exhibition"], "palette": ["olive"]},
                    )
                ]
            ),
            color_theory_repository=FakeDerivedRepository(
                [
                    KnowledgeCard(
                        id="color:1",
                        knowledge_type=KnowledgeType.COLOR_THEORY,
                        title="Color",
                        summary="Keep olive refined.",
                    )
                ]
            ),
            fashion_history_repository=FakeDerivedRepository([]),
            tailoring_principles_repository=FakeDerivedRepository(
                [
                    KnowledgeCard(
                        id="tailoring:1",
                        knowledge_type=KnowledgeType.TAILORING_PRINCIPLES,
                        title="Tailoring",
                        summary="Keep the silhouette polished.",
                    )
                ]
            ),
            materials_fabrics_repository=FakeDerivedRepository([]),
            flatlay_patterns_repository=FakeDerivedRepository([]),
            knowledge_ranker=KnowledgeRanker(),
            knowledge_bundle_builder=KnowledgeBundleBuilder(),
        )

        bundle = await service.retrieve(
            KnowledgeQuery(
                mode="occasion_outfit",
                occasion_context={"event_type": "exhibition", "dress_code": "smart casual", "color_preferences": ["olive"]},
                limit=6,
            )
        )

        self.assertEqual(len(bundle.style_cards), 1)
        self.assertEqual(len(bundle.color_cards), 1)
        self.assertEqual(len(bundle.tailoring_cards), 1)
