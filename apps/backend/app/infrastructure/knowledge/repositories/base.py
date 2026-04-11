from app.application.knowledge.contracts import StyleCatalogRepository
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery


class DerivedStyleKnowledgeRepository:
    def __init__(self, *, style_catalog_repository: StyleCatalogRepository) -> None:
        self.style_catalog_repository = style_catalog_repository

    async def resolve_style_cards(
        self,
        *,
        query: KnowledgeQuery,
        context_style_cards: list[KnowledgeCard] | None = None,
    ) -> list[KnowledgeCard]:
        if context_style_cards:
            return context_style_cards
        return await self.style_catalog_repository.search(query=query)
