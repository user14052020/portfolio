from typing import Protocol

from app.application.knowledge.contracts import KnowledgeProvider
from app.domain.knowledge.entities import (
    KnowledgeCard,
    KnowledgeProviderConfig,
    KnowledgeQuery,
    StyleKnowledgeProjectionResult,
)
from app.domain.knowledge.enums import KnowledgeType


class StyleDistilledProjectionRepository(Protocol):
    async def search_projections(self, *, query: KnowledgeQuery) -> list[StyleKnowledgeProjectionResult]:
        ...


class StyleDistilledKnowledgeProvider(KnowledgeProvider):
    def __init__(
        self,
        *,
        projection_repository: StyleDistilledProjectionRepository,
        config: KnowledgeProviderConfig | None = None,
    ) -> None:
        self._projection_repository = projection_repository
        self.config = config or KnowledgeProviderConfig(
            code="style_ingestion",
            name="Style Ingestion",
            provider_type="distilled_style",
            is_enabled=True,
            is_runtime_enabled=True,
            is_ingestion_enabled=False,
            priority=10,
            runtime_roles=["reasoning", "profile_alignment", "voice", "generation"],
        )

    async def search(self, *, query: KnowledgeQuery) -> list[KnowledgeCard]:
        projections = await self._projection_repository.search_projections(query=query)
        cards: list[KnowledgeCard] = []
        seen_ids: set[str] = set()
        for projection in projections:
            projected_cards = [card for card in projection.cards if card.is_active and self._is_relevant(card=card, query=query)]
            if not projected_cards:
                fallback = projection.primary_runtime_card()
                projected_cards = [fallback] if fallback is not None and fallback.is_active else []
            for card in projected_cards:
                if card.id in seen_ids:
                    continue
                seen_ids.add(card.id)
                cards.append(card)
        return cards

    def _is_relevant(self, *, card: KnowledgeCard, query: KnowledgeQuery) -> bool:
        knowledge_type = card.knowledge_type
        if knowledge_type in _BASE_KNOWLEDGE_TYPES:
            return True
        if knowledge_type in _STYLING_KNOWLEDGE_TYPES and (
            query.need_styling_rules or query.mode in {"style_exploration", "garment_matching", "occasion_outfit"}
        ):
            return True
        if knowledge_type in _VISUAL_KNOWLEDGE_TYPES and (
            query.need_visual_knowledge
            or query.need_color_poetics
            or query.retrieval_profile == "visual_heavy"
            or query.mode == "visual_offer"
        ):
            return True
        if knowledge_type in _HISTORICAL_KNOWLEDGE_TYPES and (
            query.need_historical_knowledge or query.mode in {"general_advice", "style_exploration", "occasion_outfit"}
        ):
            return True
        return False


_BASE_KNOWLEDGE_TYPES = {
    KnowledgeType.STYLE_CATALOG,
    KnowledgeType.STYLE_DESCRIPTION,
}

_STYLING_KNOWLEDGE_TYPES = {
    KnowledgeType.STYLE_STYLING_RULES,
    KnowledgeType.STYLE_CASUAL_ADAPTATIONS,
    KnowledgeType.STYLE_NEGATIVE_GUIDANCE,
    KnowledgeType.STYLE_SIGNATURE_DETAILS,
}

_VISUAL_KNOWLEDGE_TYPES = {
    KnowledgeType.STYLE_VISUAL_LANGUAGE,
    KnowledgeType.STYLE_IMAGE_COMPOSITION,
    KnowledgeType.STYLE_PROPS,
    KnowledgeType.STYLE_PALETTE_LOGIC,
    KnowledgeType.STYLE_PHOTO_TREATMENT,
}

_HISTORICAL_KNOWLEDGE_TYPES = {
    KnowledgeType.STYLE_RELATION_CONTEXT,
    KnowledgeType.STYLE_BRANDS_PLATFORMS,
}
