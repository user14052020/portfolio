import unittest

from app.application.knowledge.services.knowledge_providers_registry import (
    DefaultKnowledgeProvidersRegistry,
)
from app.domain.knowledge.entities import KnowledgeProviderConfig, KnowledgeQuery, KnowledgeRuntimeFlags
from app.domain.knowledge_runtime_settings import KnowledgeRuntimeSettings
from app.infrastructure.knowledge.style_distilled_knowledge_provider import StyleDistilledKnowledgeProvider


class FakeKnowledgeProvider:
    def __init__(self, config: KnowledgeProviderConfig) -> None:
        self.config = config

    async def search(self, *, query: KnowledgeQuery):
        return []


class FakeKnowledgeRuntimeSettingsProvider:
    def __init__(self, settings: KnowledgeRuntimeSettings) -> None:
        self._settings = settings

    async def get_runtime_flags(self) -> KnowledgeRuntimeFlags:
        return self._settings.runtime_flags()

    async def get_provider_priorities(self) -> dict[str, int]:
        return self._settings.normalized_provider_priorities()


class KnowledgeProvidersRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_registry_returns_style_ingestion_first_as_canonical_provider(self) -> None:
        style_provider = StyleDistilledKnowledgeProvider(projection_repository=FakeProjectionRepository())
        historian_provider = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="fashion_historian",
                name="Fashion Historian",
                provider_type="editorial_history",
                is_enabled=True,
                is_runtime_enabled=True,
                priority=50,
                runtime_roles=["reasoning", "historical_context"],
            )
        )
        registry = DefaultKnowledgeProvidersRegistry(
            providers=[historian_provider, style_provider],
            runtime_flags=KnowledgeRuntimeFlags(
                fashion_historian_enabled=True,
                use_historical_context=True,
            ),
        )

        providers = await registry.get_enabled_runtime_providers()

        self.assertEqual([provider.config.code for provider in providers], ["style_ingestion", "fashion_historian"])

    async def test_registry_honors_feature_flags_for_future_providers(self) -> None:
        style_provider = StyleDistilledKnowledgeProvider(projection_repository=FakeProjectionRepository())
        malevich_provider = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="malevich",
                name="Malevich",
                provider_type="color_poetics",
                is_enabled=True,
                is_runtime_enabled=True,
                priority=20,
                runtime_roles=["voice", "color_poetics"],
            )
        )
        stylist_provider = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="stylist_editorial",
                name="Stylist Editorial",
                provider_type="editorial",
                is_enabled=True,
                is_runtime_enabled=True,
                priority=30,
                runtime_roles=["voice", "editorial"],
            )
        )
        registry = DefaultKnowledgeProvidersRegistry(
            providers=[style_provider, malevich_provider, stylist_provider],
            runtime_flags=KnowledgeRuntimeFlags(
                malevich_enabled=False,
                stylist_enabled=False,
                use_color_poetics=False,
                use_editorial_knowledge=False,
            ),
        )

        providers = await registry.get_enabled_runtime_providers()

        self.assertEqual([provider.config.code for provider in providers], ["style_ingestion"])

    async def test_registry_gracefully_skips_disabled_and_duplicate_provider_entries(self) -> None:
        style_provider = StyleDistilledKnowledgeProvider(projection_repository=FakeProjectionRepository())
        duplicate_style_provider = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="style_ingestion",
                name="Shadow Style Provider",
                provider_type="distilled_style",
                is_enabled=True,
                is_runtime_enabled=True,
                priority=100,
                runtime_roles=["reasoning"],
            )
        )
        disabled_historian_provider = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="fashion_historian",
                name="Fashion Historian",
                provider_type="editorial_history",
                is_enabled=False,
                is_runtime_enabled=True,
                priority=40,
                runtime_roles=["historical_context"],
            )
        )
        registry = DefaultKnowledgeProvidersRegistry(
            providers=[duplicate_style_provider, disabled_historian_provider, style_provider],
            runtime_flags=KnowledgeRuntimeFlags(),
        )

        providers = await registry.get_enabled_runtime_providers()

        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0].config.code, "style_ingestion")

    async def test_registry_keeps_style_ingestion_first_while_applying_dynamic_priority_overrides(self) -> None:
        style_provider = StyleDistilledKnowledgeProvider(projection_repository=FakeProjectionRepository())
        historian_provider = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="fashion_historian",
                name="Fashion Historian",
                provider_type="editorial_history",
                is_enabled=True,
                is_runtime_enabled=True,
                priority=50,
                runtime_roles=["reasoning", "historical_context"],
            )
        )
        editorial_provider = FakeKnowledgeProvider(
            KnowledgeProviderConfig(
                code="stylist_editorial",
                name="Stylist Editorial",
                provider_type="editorial",
                is_enabled=True,
                is_runtime_enabled=True,
                priority=60,
                runtime_roles=["voice", "editorial"],
            )
        )
        registry = DefaultKnowledgeProvidersRegistry(
            providers=[style_provider, historian_provider, editorial_provider],
            runtime_settings_provider=FakeKnowledgeRuntimeSettingsProvider(
                KnowledgeRuntimeSettings(
                    fashion_historian_enabled=True,
                    stylist_enabled=True,
                    use_editorial_knowledge=True,
                    use_historical_context=True,
                    provider_priorities={
                        "style_ingestion": 20,
                        "fashion_historian": 30,
                        "stylist_editorial": 5,
                    },
                )
            ),
        )

        providers = await registry.get_enabled_runtime_providers()

        self.assertEqual(
            [provider.config.code for provider in providers],
            ["style_ingestion", "stylist_editorial", "fashion_historian"],
        )


class FakeProjectionRepository:
    async def search_projections(self, *, query: KnowledgeQuery):
        return []
