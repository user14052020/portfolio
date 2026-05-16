import unittest

from app.application.knowledge.services.knowledge_context_assembler import (
    DefaultKnowledgeContextAssembler,
)
from app.application.knowledge.services.knowledge_providers_registry import (
    DefaultKnowledgeProvidersRegistry,
)
from app.application.knowledge.services.knowledge_ranker import KnowledgeRanker
from app.application.knowledge.use_cases.preview_knowledge_retrieval import (
    PreviewKnowledgeRetrievalUseCase,
)
from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_context import ChatModeContext
from app.domain.knowledge.entities import (
    KnowledgeCard,
    KnowledgeProviderConfig,
    KnowledgeRuntimeFlags,
)
from app.domain.knowledge.enums import KnowledgeType


class _FakeRuntimeSettingsProvider:
    def __init__(
        self,
        *,
        runtime_flags: KnowledgeRuntimeFlags | None = None,
        provider_priorities: dict[str, int] | None = None,
    ) -> None:
        self.runtime_flags = runtime_flags or KnowledgeRuntimeFlags()
        self.provider_priorities = dict(provider_priorities or {})

    async def get_runtime_flags(self) -> KnowledgeRuntimeFlags:
        return self.runtime_flags

    async def get_provider_priorities(self) -> dict[str, int]:
        return dict(self.provider_priorities)


class _FakeKnowledgeProvider:
    def __init__(self, config: KnowledgeProviderConfig, cards: list[KnowledgeCard]) -> None:
        self.config = config
        self._cards = list(cards)
        self.query = None

    async def search(self, *, query):
        self.query = query
        return list(self._cards)


class PreviewKnowledgeRetrievalUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_preview_returns_central_knowledge_context_with_query_overrides(self) -> None:
        style_provider = _FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="style_ingestion",
                name="Style Ingestion",
                provider_type="distilled_style",
                priority=10,
                runtime_roles=["reasoning", "voice"],
            ),
            [
                self._card("style_catalog:neo-classic", KnowledgeType.STYLE_CATALOG),
                self._card("style_visual:neo-classic", KnowledgeType.STYLE_VISUAL_LANGUAGE),
                self._card("style_rules:neo-classic", KnowledgeType.STYLE_STYLING_RULES),
            ],
        )
        settings_provider = _FakeRuntimeSettingsProvider(
            runtime_flags=KnowledgeRuntimeFlags(
                style_ingestion_enabled=True,
                use_historical_context=True,
                use_color_poetics=True,
            ),
            provider_priorities={"style_ingestion": 7},
        )
        registry = DefaultKnowledgeProvidersRegistry(
            providers=[style_provider],
            runtime_settings_provider=settings_provider,
        )
        assembler = DefaultKnowledgeContextAssembler(
            providers_registry=registry,
            knowledge_card_ranker=KnowledgeRanker(),
        )
        use_case = PreviewKnowledgeRetrievalUseCase(
            knowledge_context_assembler=assembler,
            providers_registry=registry,
            runtime_settings_provider=settings_provider,
        )

        result = await use_case.execute(
            command=ChatCommand(
                session_id="preview-session",
                locale="en",
                message="Show me a refined classic direction",
                profile_context={"presentation_profile": "feminine"},
            ),
            context=ChatModeContext(current_style_id="neo-classic"),
            mode="style_exploration",
            style_id="neo-classic",
            limit=5,
            query_overrides={
                "style_ids": ["neo-classic", "new-romantic"],
                "style_families": ["classic", "romantic"],
                "retrieval_profile": "visual_heavy",
                "need_visual_knowledge": True,
                "need_styling_rules": True,
                "user_request": "Need strong visual language",
            },
        )

        self.assertEqual(result.knowledge_query.style_id, "neo-classic")
        self.assertEqual(result.knowledge_query.style_ids, ["neo-classic", "new-romantic"])
        self.assertEqual(result.knowledge_query.style_families, ["classic", "romantic"])
        self.assertEqual(result.knowledge_query.retrieval_profile, "visual_heavy")
        self.assertTrue(result.knowledge_query.need_visual_knowledge)
        self.assertTrue(result.knowledge_query.need_styling_rules)
        self.assertEqual(result.knowledge_query.user_request, "Need strong visual language")
        self.assertEqual(len(result.knowledge_context.knowledge_cards), 3)
        self.assertEqual(result.knowledge_context.observability["knowledge_providers_used"], ["style_ingestion"])
        self.assertEqual(result.runtime_flags.model_dump(mode="json")["style_ingestion_enabled"], True)
        self.assertEqual(result.provider_priorities["style_ingestion"], 7)
        self.assertEqual(result.enabled_runtime_providers[0].code, "style_ingestion")
        self.assertEqual(style_provider.query.retrieval_profile, "visual_heavy")

    async def test_preview_reflects_disabled_runtime_provider(self) -> None:
        style_provider = _FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="style_ingestion",
                name="Style Ingestion",
                provider_type="distilled_style",
                priority=10,
                runtime_roles=["reasoning"],
            ),
            [self._card("style_catalog:soft-prep", KnowledgeType.STYLE_CATALOG)],
        )
        settings_provider = _FakeRuntimeSettingsProvider(
            runtime_flags=KnowledgeRuntimeFlags(style_ingestion_enabled=False),
            provider_priorities={"style_ingestion": 10},
        )
        registry = DefaultKnowledgeProvidersRegistry(
            providers=[style_provider],
            runtime_settings_provider=settings_provider,
        )
        assembler = DefaultKnowledgeContextAssembler(providers_registry=registry)
        use_case = PreviewKnowledgeRetrievalUseCase(
            knowledge_context_assembler=assembler,
            providers_registry=registry,
            runtime_settings_provider=settings_provider,
        )

        result = await use_case.execute(
            command=ChatCommand(
                session_id="preview-session",
                locale="en",
                message="Find prep styles",
                profile_context={},
            ),
            context=ChatModeContext(),
            mode="general_advice",
            limit=4,
        )

        self.assertEqual(result.enabled_runtime_providers, [])
        self.assertTrue(result.knowledge_context.is_empty())
        self.assertEqual(result.knowledge_context.observability["knowledge_provider_count"], 0)
        self.assertEqual(result.knowledge_context.observability["knowledge_providers_used"], [])

    def _card(self, card_id: str, knowledge_type: KnowledgeType) -> KnowledgeCard:
        return KnowledgeCard(
            id=card_id,
            knowledge_type=knowledge_type,
            provider_code="style_ingestion",
            provider_priority=10,
            title=card_id,
            summary=f"{knowledge_type.value} summary",
            style_id=card_id.split(":")[-1],
            is_active=True,
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
