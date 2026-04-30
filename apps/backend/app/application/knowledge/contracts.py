from typing import Protocol

from app.domain.knowledge.entities import (
    KnowledgeBundle,
    KnowledgeCard,
    KnowledgeProviderConfig,
    KnowledgeQuery,
    KnowledgeRuntimeFlags,
    StyleKnowledgeProjectionResult,
)
from app.domain.reasoning.entities.knowledge_context import KnowledgeContext


class KnowledgeProvider(Protocol):
    config: KnowledgeProviderConfig

    async def search(self, *, query: KnowledgeQuery) -> list[KnowledgeCard]:
        ...


class KnowledgeProvidersRegistry(Protocol):
    async def get_enabled_runtime_providers(self) -> list[KnowledgeProvider]:
        ...


class KnowledgeRuntimeSettingsProvider(Protocol):
    async def get_runtime_flags(self) -> KnowledgeRuntimeFlags:
        ...

    async def get_provider_priorities(self) -> dict[str, int]:
        ...


class KnowledgeContextAssembler(Protocol):
    async def assemble(self, query: KnowledgeQuery) -> KnowledgeContext:
        ...


class KnowledgeCardRanker(Protocol):
    async def rank(self, *, query: KnowledgeQuery, cards: list[KnowledgeCard]) -> list[KnowledgeCard]:
        ...


class StyleFacetKnowledgeProjector(Protocol):
    async def project(self, *, style_id: int) -> StyleKnowledgeProjectionResult:
        ...


class StyleCatalogRepository(Protocol):
    async def search(self, *, query: KnowledgeQuery) -> list[KnowledgeCard]:
        ...

    async def list_candidate_styles(
        self,
        *,
        limit: int,
        exclude_style_ids: list[str] | None = None,
    ) -> list[KnowledgeCard]:
        ...


class ColorTheoryRepository(Protocol):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        ...


class FashionHistoryRepository(Protocol):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        ...


class TailoringPrinciplesRepository(Protocol):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        ...


class MaterialsFabricsRepository(Protocol):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        ...


class FlatlayPatternsRepository(Protocol):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        ...


class KnowledgeSearchAdapter(Protocol):
    def expand_terms(self, *, query: KnowledgeQuery) -> list[str]:
        ...


class KnowledgeCache(Protocol):
    async def get(self, *, cache_key: str) -> KnowledgeBundle | None:
        ...

    async def set(self, *, cache_key: str, bundle: KnowledgeBundle) -> None:
        ...


class KnowledgeRetrievalService(Protocol):
    async def retrieve(self, query: KnowledgeQuery) -> KnowledgeBundle:
        ...
