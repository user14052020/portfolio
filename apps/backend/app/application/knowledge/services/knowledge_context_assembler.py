import inspect
from time import perf_counter
from typing import Any

from app.application.knowledge.contracts import KnowledgeCardRanker, KnowledgeProvider, KnowledgeProvidersRegistry
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType
from app.domain.reasoning.entities.knowledge_context import KnowledgeContext, StyleKnowledgeCard


class DefaultKnowledgeContextAssembler:
    def __init__(
        self,
        *,
        providers_registry: KnowledgeProvidersRegistry,
        knowledge_card_ranker: KnowledgeCardRanker | None = None,
    ) -> None:
        self._providers_registry = providers_registry
        self._knowledge_card_ranker = knowledge_card_ranker

    async def assemble(self, query: KnowledgeQuery) -> KnowledgeContext:
        providers = await self._providers_registry.get_enabled_runtime_providers()
        cards: list[KnowledgeCard] = []
        providers_used: list[str] = []
        empty_providers: list[str] = []
        provider_card_counts: dict[str, int] = {}
        provider_latency_ms: dict[str, int] = {}
        seen_ids: set[str] = set()
        duplicate_cards_filtered_count = 0

        for provider in providers:
            started_at = perf_counter()
            provider_cards = await provider.search(query=query)
            provider_code = provider.config.code
            provider_latency_ms[provider_code] = max(int((perf_counter() - started_at) * 1000), 0)
            provider_card_counts[provider_code] = len(provider_cards)
            if not provider_cards:
                empty_providers.append(provider_code)
                continue
            providers_used.append(provider_code)
            for card in provider_cards:
                if card.id in seen_ids:
                    duplicate_cards_filtered_count += 1
                    continue
                seen_ids.add(card.id)
                cards.append(card)

        ranked_cards = await self._rank_cards(query=query, cards=cards)
        limit = max(query.limit, 1)
        total_ranked_cards = ranked_cards[: limit * 4]
        style_cards = _style_cards(ranked_cards, limit=limit)
        style_advice_cards = _cards_by_type(ranked_cards, _STYLE_ADVICE_TYPES, limit=limit)
        style_visual_cards = _cards_by_type(ranked_cards, _STYLE_VISUAL_TYPES, limit=limit)
        style_history_cards = _cards_by_type(ranked_cards, _STYLE_HISTORY_TYPES, limit=limit)
        editorial_cards = _editorial_cards(ranked_cards, limit=limit)
        return KnowledgeContext(
            providers_used=providers_used,
            knowledge_cards=total_ranked_cards,
            style_cards=style_cards,
            style_advice_cards=style_advice_cards,
            style_visual_cards=style_visual_cards,
            style_history_cards=style_history_cards,
            editorial_cards=editorial_cards,
            observability=_observability(
                query=query,
                providers=providers,
                providers_used=providers_used,
                provider_card_counts=provider_card_counts,
                provider_latency_ms=provider_latency_ms,
                empty_providers=empty_providers,
                duplicate_cards_filtered_count=duplicate_cards_filtered_count,
                ranked_cards=ranked_cards,
                returned_cards=total_ranked_cards,
                ranking_applied=self._knowledge_card_ranker is not None and bool(cards),
            ),
        )

    async def _rank_cards(self, *, query: KnowledgeQuery, cards: list[KnowledgeCard]) -> list[KnowledgeCard]:
        if self._knowledge_card_ranker is None or not cards:
            return list(cards)
        ranked = self._knowledge_card_ranker.rank(query=query, cards=list(cards))
        if inspect.isawaitable(ranked):
            ranked = await ranked
        return list(ranked)


_STYLE_CARD_TYPES = {
    KnowledgeType.STYLE_CATALOG,
    KnowledgeType.STYLE_DESCRIPTION,
}

_STYLE_ADVICE_TYPES = {
    KnowledgeType.STYLE_STYLING_RULES,
    KnowledgeType.STYLE_CASUAL_ADAPTATIONS,
    KnowledgeType.STYLE_SIGNATURE_DETAILS,
    KnowledgeType.STYLE_NEGATIVE_GUIDANCE,
}

_STYLE_VISUAL_TYPES = {
    KnowledgeType.STYLE_VISUAL_LANGUAGE,
    KnowledgeType.STYLE_IMAGE_COMPOSITION,
    KnowledgeType.STYLE_PROPS,
    KnowledgeType.STYLE_PALETTE_LOGIC,
    KnowledgeType.STYLE_PHOTO_TREATMENT,
}

_STYLE_HISTORY_TYPES = {
    KnowledgeType.STYLE_RELATION_CONTEXT,
    KnowledgeType.STYLE_BRANDS_PLATFORMS,
    KnowledgeType.FASHION_HISTORY,
    KnowledgeType.STYLE_HISTORY,
}


def _style_cards(cards: list[KnowledgeCard], *, limit: int) -> list[StyleKnowledgeCard]:
    result: list[StyleKnowledgeCard] = []
    seen_style_ids: set[str] = set()
    for card in cards:
        if card.knowledge_type not in _STYLE_CARD_TYPES:
            continue
        style_id = (card.style_id or card.id).strip() if isinstance(card.style_id or card.id, str) else str(card.style_id or card.id)
        lowered = style_id.lower()
        if not style_id or lowered in seen_style_ids:
            continue
        seen_style_ids.add(lowered)
        result.append(
            StyleKnowledgeCard(
                style_id=card.style_id or card.id,
                title=card.title,
                summary=card.summary,
                tags=list(card.tags),
                confidence=card.confidence,
                source_ref=card.source_ref,
            )
        )
        if len(result) >= limit:
            break
    return result


def _cards_by_type(cards: list[KnowledgeCard], allowed_types: set[KnowledgeType], *, limit: int) -> list[KnowledgeCard]:
    result = [card for card in cards if card.knowledge_type in allowed_types]
    return result[:limit]


def _editorial_cards(cards: list[KnowledgeCard], *, limit: int) -> list[KnowledgeCard]:
    result = [
        card
        for card in cards
        if isinstance(card.provider_code, str)
        and card.provider_code.strip()
        and card.provider_code.strip().lower() != "style_ingestion"
    ]
    return result[:limit]


def _observability(
    *,
    query: KnowledgeQuery,
    providers: list[KnowledgeProvider],
    providers_used: list[str],
    provider_card_counts: dict[str, int],
    provider_latency_ms: dict[str, int],
    empty_providers: list[str],
    duplicate_cards_filtered_count: int,
    ranked_cards: list[KnowledgeCard],
    returned_cards: list[KnowledgeCard],
    ranking_applied: bool,
) -> dict[str, Any]:
    cards_filtered_out_count = max(len(ranked_cards) - len(returned_cards), 0) + duplicate_cards_filtered_count
    style_provider_cards = [
        card
        for card in ranked_cards
        if isinstance(card.provider_code, str) and card.provider_code.strip().lower() == "style_ingestion"
    ]
    style_cards_by_style: dict[str, list[KnowledgeCard]] = {}
    for card in style_provider_cards:
        style_key = str(card.style_id or card.id).strip()
        if not style_key:
            continue
        style_cards_by_style.setdefault(style_key, []).append(card)

    low_richness_styles = sorted(
        style_id
        for style_id, cards in style_cards_by_style.items()
        if len(cards) < 3
    )
    legacy_summary_fallback_styles = sorted(
        style_id
        for style_id, cards in style_cards_by_style.items()
        if cards
        and all(card.knowledge_type in _STYLE_CARD_TYPES for card in cards)
    )
    style_provider_knowledge_types = sorted(
        {card.knowledge_type.value for card in style_provider_cards}
    )
    projection_versions = sorted(_metadata_values(style_provider_cards, "projection_version"))
    parser_versions = sorted(_metadata_values(style_provider_cards, "parser_version"))
    ranking_summary = {
        "ranking_applied": ranking_applied,
        "input_cards": sum(provider_card_counts.values()) - duplicate_cards_filtered_count,
        "ranked_cards": len(ranked_cards),
        "returned_cards": len(returned_cards),
    }
    return {
        "knowledge_query_mode": query.mode,
        "knowledge_retrieval_profile": query.retrieval_profile,
        "knowledge_provider_count": len(providers),
        "knowledge_providers_used": list(providers_used),
        "knowledge_cards_per_provider": dict(provider_card_counts),
        "knowledge_empty_providers": list(empty_providers),
        "knowledge_provider_latency_ms": dict(provider_latency_ms),
        "knowledge_duplicate_cards_filtered_count": duplicate_cards_filtered_count,
        "knowledge_cards_filtered_out_count": cards_filtered_out_count,
        "knowledge_ranking_summary": ranking_summary,
        "style_provider_projected_cards_count": len(style_provider_cards),
        "style_provider_knowledge_types": style_provider_knowledge_types,
        "style_provider_projection_versions": projection_versions,
        "style_provider_parser_versions": parser_versions,
        "style_provider_low_richness_styles": low_richness_styles,
        "style_provider_legacy_summary_fallback_styles": legacy_summary_fallback_styles,
    }


def _metadata_values(cards: list[KnowledgeCard], key: str) -> set[str]:
    values: set[str] = set()
    for card in cards:
        raw = card.metadata.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            values.add(text)
    return values
