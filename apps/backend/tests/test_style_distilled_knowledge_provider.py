import unittest

from app.domain.knowledge.entities import (
    KnowledgeCard,
    KnowledgeQuery,
    StyleKnowledgeProjectionResult,
)
from app.domain.knowledge.enums import KnowledgeType
from app.infrastructure.knowledge.style_distilled_knowledge_provider import StyleDistilledKnowledgeProvider


class FakeProjectionRepository:
    def __init__(self, projections: list[StyleKnowledgeProjectionResult]) -> None:
        self._projections = list(projections)
        self.query: KnowledgeQuery | None = None

    async def search_projections(self, *, query: KnowledgeQuery) -> list[StyleKnowledgeProjectionResult]:
        self.query = query
        return list(self._projections)


class StyleDistilledKnowledgeProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_returns_distilled_cards_for_runtime_retrieval(self) -> None:
        repository = FakeProjectionRepository(
            [
                StyleKnowledgeProjectionResult(
                    provider_code="style_ingestion",
                    style_id=1,
                    style_slug="soft-retro-prep",
                    style_name="Soft Retro Prep",
                    projection_version="style-facet-projector.v1",
                    facet_version="2026-04",
                    cards=[
                        self._card("style_catalog:soft-retro-prep", KnowledgeType.STYLE_CATALOG),
                        self._card("style_description:soft-retro-prep", KnowledgeType.STYLE_DESCRIPTION),
                        self._card("style_rules:soft-retro-prep", KnowledgeType.STYLE_STYLING_RULES),
                        self._card("style_visual:soft-retro-prep", KnowledgeType.STYLE_VISUAL_LANGUAGE),
                        self._card("style_relation:soft-retro-prep", KnowledgeType.STYLE_RELATION_CONTEXT),
                    ],
                )
            ]
        )
        provider = StyleDistilledKnowledgeProvider(projection_repository=repository)

        cards = await provider.search(
            query=KnowledgeQuery(
                mode="style_exploration",
                style_id="soft-retro-prep",
                need_visual_knowledge=True,
                need_historical_knowledge=True,
                need_styling_rules=True,
            )
        )

        self.assertEqual(
            [card.knowledge_type for card in cards],
            [
                KnowledgeType.STYLE_CATALOG,
                KnowledgeType.STYLE_DESCRIPTION,
                KnowledgeType.STYLE_STYLING_RULES,
                KnowledgeType.STYLE_VISUAL_LANGUAGE,
                KnowledgeType.STYLE_RELATION_CONTEXT,
            ],
        )
        self.assertEqual(repository.query.style_id, "soft-retro-prep")

    async def test_provider_keeps_compatibility_card_when_style_is_low_richness(self) -> None:
        repository = FakeProjectionRepository(
            [
                StyleKnowledgeProjectionResult(
                    provider_code="style_ingestion",
                    style_id=2,
                    style_slug="minimal-uniform",
                    style_name="Minimal Uniform",
                    projection_version="style-facet-projector.v1",
                    cards=[
                        self._card(
                            "style_catalog:minimal-uniform",
                            KnowledgeType.STYLE_CATALOG,
                            style_id="minimal-uniform",
                        ),
                    ],
                )
            ]
        )
        provider = StyleDistilledKnowledgeProvider(projection_repository=repository)

        cards = await provider.search(
            query=KnowledgeQuery(
                mode="general_advice",
                style_id="minimal-uniform",
                need_visual_knowledge=True,
                need_historical_knowledge=True,
                need_styling_rules=True,
                need_color_poetics=True,
            )
        )

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].knowledge_type, KnowledgeType.STYLE_CATALOG)
        self.assertEqual(cards[0].provider_code, "style_ingestion")

    def test_provider_uses_style_ingestion_as_first_canonical_config(self) -> None:
        provider = StyleDistilledKnowledgeProvider(projection_repository=FakeProjectionRepository([]))

        self.assertEqual(provider.config.code, "style_ingestion")
        self.assertEqual(provider.config.provider_type, "distilled_style")
        self.assertTrue(provider.config.is_available_for_runtime())
        self.assertIn("reasoning", provider.config.runtime_roles)

    def _card(
        self,
        card_id: str,
        knowledge_type: KnowledgeType,
        *,
        style_id: str = "soft-retro-prep",
    ) -> KnowledgeCard:
        return KnowledgeCard(
            id=card_id,
            knowledge_type=knowledge_type,
            provider_code="style_ingestion",
            provider_priority=10,
            title=card_id,
            summary=f"{knowledge_type.value} summary",
            style_id=style_id,
            is_active=True,
            metadata={},
        )
