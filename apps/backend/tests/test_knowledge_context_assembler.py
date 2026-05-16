import unittest

from app.application.knowledge.services.knowledge_context_assembler import (
    DefaultKnowledgeContextAssembler,
)
from app.application.knowledge.services.knowledge_providers_registry import (
    DefaultKnowledgeProvidersRegistry,
)
from app.application.knowledge.services.knowledge_ranker import KnowledgeRanker
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeProviderConfig, KnowledgeQuery, KnowledgeRuntimeFlags
from app.domain.knowledge.enums import KnowledgeType
from app.infrastructure.knowledge.style_distilled_knowledge_provider import StyleDistilledKnowledgeProvider


class FakeProjectionRepository:
    async def search_projections(self, *, query: KnowledgeQuery):
        return []


class FakeKnowledgeProvider:
    def __init__(self, config: KnowledgeProviderConfig, cards: list[KnowledgeCard]) -> None:
        self.config = config
        self._cards = list(cards)
        self.query: KnowledgeQuery | None = None

    async def search(self, *, query: KnowledgeQuery) -> list[KnowledgeCard]:
        self.query = query
        return list(self._cards)


class KnowledgeContextAssemblerTests(unittest.IsolatedAsyncioTestCase):
    async def test_assembler_shapes_style_provider_cards_into_typed_context(self) -> None:
        style_provider = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="style_ingestion",
                name="Style Ingestion",
                provider_type="distilled_style",
                priority=10,
                runtime_roles=["reasoning"],
            ),
            [
                self._card("style_catalog:soft-retro-prep", KnowledgeType.STYLE_CATALOG),
                self._card("style_description:soft-retro-prep", KnowledgeType.STYLE_DESCRIPTION),
                self._card("style_rules:soft-retro-prep", KnowledgeType.STYLE_STYLING_RULES),
                self._card("style_visual:soft-retro-prep", KnowledgeType.STYLE_VISUAL_LANGUAGE),
                self._card("style_history:soft-retro-prep", KnowledgeType.STYLE_RELATION_CONTEXT),
            ],
        )
        registry = DefaultKnowledgeProvidersRegistry(
            providers=[style_provider],
            runtime_flags=KnowledgeRuntimeFlags(),
        )
        assembler = DefaultKnowledgeContextAssembler(
            providers_registry=registry,
            knowledge_card_ranker=KnowledgeRanker(),
        )

        context = await assembler.assemble(
            KnowledgeQuery(
                mode="style_exploration",
                style_id="soft-retro-prep",
                retrieval_profile="visual_heavy",
                need_visual_knowledge=True,
                need_historical_knowledge=True,
                need_styling_rules=True,
                limit=6,
            )
        )

        self.assertEqual(context.providers_used, ["style_ingestion"])
        self.assertEqual(len(context.knowledge_cards), 5)
        self.assertEqual(len(context.style_cards), 1)
        self.assertEqual(len(context.style_advice_cards), 1)
        self.assertEqual(len(context.style_visual_cards), 1)
        self.assertEqual(len(context.style_history_cards), 1)
        self.assertEqual(len(context.editorial_cards), 0)
        self.assertEqual(style_provider.query.retrieval_profile, "visual_heavy")
        self.assertEqual(context.observability["knowledge_query_mode"], "style_exploration")
        self.assertEqual(context.observability["knowledge_retrieval_profile"], "visual_heavy")
        self.assertEqual(context.observability["knowledge_provider_count"], 1)
        self.assertEqual(context.observability["knowledge_providers_used"], ["style_ingestion"])
        self.assertEqual(context.observability["knowledge_cards_per_provider"]["style_ingestion"], 5)
        self.assertEqual(context.observability["knowledge_empty_providers"], [])
        self.assertIn("style_catalog", context.observability["style_provider_knowledge_types"])
        self.assertTrue(context.observability["knowledge_ranking_summary"]["ranking_applied"])

    async def test_assembler_gracefully_skips_empty_editorial_provider(self) -> None:
        style_provider = StyleDistilledKnowledgeProvider(projection_repository=FakeProjectionRepository())
        empty_historian = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="fashion_historian",
                name="Historian",
                provider_type="editorial_history",
                is_enabled=True,
                is_runtime_enabled=True,
                priority=50,
                runtime_roles=["historical_context"],
            ),
            [],
        )
        registry = DefaultKnowledgeProvidersRegistry(
            providers=[style_provider, empty_historian],
            runtime_flags=KnowledgeRuntimeFlags(
                fashion_historian_enabled=True,
                use_historical_context=True,
            ),
        )
        assembler = DefaultKnowledgeContextAssembler(providers_registry=registry)

        context = await assembler.assemble(KnowledgeQuery(mode="general_advice", limit=4))

        self.assertEqual(context.providers_used, [])
        self.assertTrue(context.is_empty())
        self.assertEqual(
            context.observability["knowledge_empty_providers"],
            ["style_ingestion", "fashion_historian"],
        )
        self.assertEqual(context.observability["knowledge_cards_per_provider"]["fashion_historian"], 0)
        self.assertEqual(context.observability["knowledge_provider_count"], 2)

    async def test_assembler_includes_future_historian_cards_and_editorial_bucket(self) -> None:
        style_provider = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="style_ingestion",
                name="Style Ingestion",
                provider_type="distilled_style",
                priority=10,
                runtime_roles=["reasoning"],
            ),
            [self._card("style_catalog:artful-minimalism", KnowledgeType.STYLE_CATALOG, title="Artful Minimalism")],
        )
        historian_provider = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="fashion_historian",
                name="Fashion Historian",
                provider_type="editorial_history",
                priority=40,
                runtime_roles=["historical_context", "editorial"],
            ),
            [
                self._card(
                    "fashion_history:artful-minimalism",
                    KnowledgeType.FASHION_HISTORY,
                    title="Historian Note",
                    provider_code="fashion_historian",
                )
            ],
        )
        registry = DefaultKnowledgeProvidersRegistry(
            providers=[historian_provider, style_provider],
            runtime_flags=KnowledgeRuntimeFlags(
                fashion_historian_enabled=True,
                use_historical_context=True,
                use_editorial_knowledge=True,
            ),
        )
        assembler = DefaultKnowledgeContextAssembler(
            providers_registry=registry,
            knowledge_card_ranker=KnowledgeRanker(),
        )

        context = await assembler.assemble(
            KnowledgeQuery(
                mode="general_advice",
                style_id="artful-minimalism",
                need_historical_knowledge=True,
                limit=5,
            )
        )

        self.assertEqual(context.providers_used, ["style_ingestion", "fashion_historian"])
        self.assertEqual(len(context.style_history_cards), 1)
        self.assertEqual(context.style_history_cards[0].provider_code, "fashion_historian")
        self.assertEqual(len(context.editorial_cards), 1)
        self.assertEqual(context.editorial_cards[0].provider_code, "fashion_historian")
        self.assertEqual(historian_provider.query.style_id, "artful-minimalism")
        self.assertEqual(
            context.observability["knowledge_providers_used"],
            ["style_ingestion", "fashion_historian"],
        )
        self.assertEqual(context.observability["knowledge_cards_per_provider"]["style_ingestion"], 1)
        self.assertEqual(context.observability["knowledge_cards_per_provider"]["fashion_historian"], 1)
        self.assertEqual(context.observability["knowledge_empty_providers"], [])

    def _card(
        self,
        card_id: str,
        knowledge_type: KnowledgeType,
        *,
        title: str | None = None,
        provider_code: str = "style_ingestion",
    ) -> KnowledgeCard:
        return KnowledgeCard(
            id=card_id,
            knowledge_type=knowledge_type,
            provider_code=provider_code,
            provider_priority=10,
            title=title or card_id,
            summary=f"{knowledge_type.value} summary",
            style_id="soft-retro-prep" if "artful-minimalism" not in card_id else "artful-minimalism",
            is_active=True,
            metadata={},
        )
