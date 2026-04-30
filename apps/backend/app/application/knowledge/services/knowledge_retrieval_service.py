from app.application.knowledge.contracts import (
    ColorTheoryRepository,
    FashionHistoryRepository,
    FlatlayPatternsRepository,
    KnowledgeCache,
    KnowledgeSearchAdapter,
    MaterialsFabricsRepository,
    StyleCatalogRepository,
    TailoringPrinciplesRepository,
)
from app.application.knowledge.services.knowledge_bundle_builder import KnowledgeBundleBuilder
from app.application.knowledge.services.knowledge_ranker import KnowledgeRanker
from app.domain.knowledge.entities import KnowledgeBundle, KnowledgeQuery


class DefaultKnowledgeRetrievalService:
    def __init__(
        self,
        *,
        style_catalog_repository: StyleCatalogRepository,
        color_theory_repository: ColorTheoryRepository,
        fashion_history_repository: FashionHistoryRepository,
        tailoring_principles_repository: TailoringPrinciplesRepository,
        materials_fabrics_repository: MaterialsFabricsRepository,
        flatlay_patterns_repository: FlatlayPatternsRepository,
        knowledge_ranker: KnowledgeRanker,
        knowledge_bundle_builder: KnowledgeBundleBuilder,
        knowledge_search_adapter: KnowledgeSearchAdapter | None = None,
        knowledge_cache: KnowledgeCache | None = None,
    ) -> None:
        self.style_catalog_repository = style_catalog_repository
        self.color_theory_repository = color_theory_repository
        self.fashion_history_repository = fashion_history_repository
        self.tailoring_principles_repository = tailoring_principles_repository
        self.materials_fabrics_repository = materials_fabrics_repository
        self.flatlay_patterns_repository = flatlay_patterns_repository
        self.knowledge_ranker = knowledge_ranker
        self.knowledge_bundle_builder = knowledge_bundle_builder
        self.knowledge_search_adapter = knowledge_search_adapter
        self.knowledge_cache = knowledge_cache

    async def retrieve(self, query: KnowledgeQuery) -> KnowledgeBundle:
        cache_key = query.content_hash()
        if self.knowledge_cache is not None:
            cached = await self.knowledge_cache.get(cache_key=cache_key)
            if cached is not None:
                return cached

        if self.knowledge_search_adapter is not None:
            self.knowledge_search_adapter.expand_terms(query=query)

        style_cards = await self.knowledge_ranker.rank(
            cards=await self.style_catalog_repository.search(query=query),
            query=query,
        )
        color_cards = await self.knowledge_ranker.rank(
            cards=await self.color_theory_repository.search(query=query, context_style_cards=style_cards),
            query=query,
        )
        history_cards = await self.knowledge_ranker.rank(
            cards=await self.fashion_history_repository.search(query=query, context_style_cards=style_cards),
            query=query,
        )
        tailoring_cards = await self.knowledge_ranker.rank(
            cards=await self.tailoring_principles_repository.search(query=query, context_style_cards=style_cards),
            query=query,
        )
        materials_cards = await self.knowledge_ranker.rank(
            cards=await self.materials_fabrics_repository.search(query=query, context_style_cards=style_cards),
            query=query,
        )
        flatlay_cards = await self.knowledge_ranker.rank(
            cards=await self.flatlay_patterns_repository.search(query=query, context_style_cards=style_cards),
            query=query,
        )

        bundle = self.knowledge_bundle_builder.build(
            query=query,
            style_cards=style_cards,
            color_cards=color_cards,
            history_cards=history_cards,
            tailoring_cards=tailoring_cards,
            materials_cards=materials_cards,
            flatlay_cards=flatlay_cards,
        )
        if self.knowledge_cache is not None:
            await self.knowledge_cache.set(cache_key=cache_key, bundle=bundle)
        return bundle
