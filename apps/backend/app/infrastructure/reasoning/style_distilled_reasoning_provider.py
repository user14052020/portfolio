import hashlib
from typing import Any, Protocol

from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.reasoning import (
    KnowledgeContext,
    ReasoningRetrievalQuery,
    StyleAdviceFacet,
    StyleFacetBundle,
    StyleImageFacet,
    StyleKnowledgeCard,
    StyleRelationFacet,
    StyleSemanticFragmentSummary,
    StyleVisualLanguageFacet,
)


class StyleCatalogSearchRepository(Protocol):
    async def search(self, *, query: KnowledgeQuery) -> list[KnowledgeCard]:
        ...


class StyleDistilledReasoningProvider:
    provider_name = "style_ingestion"

    def __init__(self, *, style_catalog_repository: StyleCatalogSearchRepository, limit: int = 8) -> None:
        self._style_catalog_repository = style_catalog_repository
        self._limit = limit

    async def retrieve(self, *, query: ReasoningRetrievalQuery) -> KnowledgeContext:
        cards = await self._search_cards(query=query)
        return KnowledgeContext(
            providers_used=[self.provider_name],
            knowledge_cards=cards,
            style_cards=[_style_card(card) for card in cards],
            style_advice_cards=[card for card in cards if _has_advice(card)],
            style_visual_cards=[card for card in cards if _has_visual_or_image(card)],
        )

    async def load_facets(self, *, query: ReasoningRetrievalQuery) -> StyleFacetBundle:
        cards = await self._search_cards(query=query)
        return StyleFacetBundle(
            advice_facets=[_advice_facet(card) for card in cards if _has_advice(card)],
            image_facets=[_image_facet(card) for card in cards if _has_image(card)],
            visual_language_facets=[_visual_language_facet(card) for card in cards if _has_visual(card)],
            relation_facets=[_relation_facet(card) for card in cards if _has_relation(card)],
        )

    async def load_fragments(self, *, query: ReasoningRetrievalQuery) -> list[StyleSemanticFragmentSummary]:
        cards = await self._search_cards(query=query)
        fragments: list[StyleSemanticFragmentSummary] = []
        for card in cards:
            fragments.extend(_semantic_fragments(card))
        return fragments

    async def _search_cards(self, *, query: ReasoningRetrievalQuery) -> list[KnowledgeCard]:
        return await self._style_catalog_repository.search(query=_knowledge_query(query, self._limit))


def _knowledge_query(query: ReasoningRetrievalQuery, limit: int) -> KnowledgeQuery:
    style_id = _style_id(query)
    return KnowledgeQuery(
        mode=query.mode,
        style_id=style_id,
        style_ids=[style_id] if style_id is not None else [],
        style_name=_style_name(query),
        style_families=_string_values(
            query.metadata.get("style_families"),
            query.active_slots.get("style_family"),
        ),
        eras=_string_values(
            query.metadata.get("style_eras"),
            query.metadata.get("eras"),
            query.active_slots.get("era"),
        ),
        intent="visual" if query.generation_intent else "advice",
        limit=_limit_for_profile(query.retrieval_profile, limit),
        message=query.user_request,
        user_request=query.user_request,
        profile_context=query.profile_context.values if query.profile_context is not None else {},
        retrieval_profile=query.retrieval_profile,
        need_visual_knowledge=query.generation_intent or query.mode in {"visual_offer", "style_exploration"},
        need_historical_knowledge=query.mode in {"general_advice", "style_exploration", "occasion_outfit"},
        need_styling_rules=query.mode in {"style_exploration", "occasion_outfit", "garment_matching"},
        need_color_poetics=query.generation_intent or query.mode in {"style_exploration", "general_advice"},
    )


def _style_id(query: ReasoningRetrievalQuery) -> str | None:
    if isinstance(query.current_style_id, str) and query.current_style_id.strip():
        return query.current_style_id.strip()
    metadata_style_id = query.metadata.get("style_id") or query.metadata.get("style_slug")
    if isinstance(metadata_style_id, str) and metadata_style_id.strip():
        return metadata_style_id.strip()
    return None


def _style_name(query: ReasoningRetrievalQuery) -> str | None:
    for value in (
        query.current_style_name,
        query.active_slots.get("style_name"),
        query.active_slots.get("style_direction"),
        query.active_slots.get("style"),
        query.user_request,
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _limit_for_profile(retrieval_profile: str | None, default_limit: int) -> int:
    if retrieval_profile == "light":
        return min(default_limit, 3)
    if retrieval_profile == "visual_heavy":
        return max(default_limit, 10)
    return default_limit


def _style_card(card: KnowledgeCard) -> StyleKnowledgeCard:
    return StyleKnowledgeCard(
        style_id=card.style_id or card.id,
        title=card.title,
        summary=card.summary,
        tags=list(card.tags),
        confidence=card.confidence,
        source_ref=card.source_ref,
    )


def _advice_facet(card: KnowledgeCard) -> StyleAdviceFacet:
    metadata = card.metadata
    return StyleAdviceFacet(
        style_id=_facet_style_id(card),
        core_style_logic=_string_list(metadata.get("core_style_logic")),
        styling_rules=_string_list(metadata.get("styling_rules")),
        casual_adaptations=_string_list(metadata.get("casual_adaptations")),
        statement_pieces=_string_list(metadata.get("statement_pieces")),
        status_markers=_string_list(metadata.get("status_markers")),
        overlap_context=_string_list(metadata.get("overlap_context")),
        historical_notes=_string_list(metadata.get("historical_notes"))
        or _string_list(metadata.get("historical_context")),
        negative_guidance=_string_list(metadata.get("negative_guidance"))
        or _string_list(metadata.get("negative_constraints")),
    )


def _image_facet(card: KnowledgeCard) -> StyleImageFacet:
    metadata = card.metadata
    return StyleImageFacet(
        style_id=_facet_style_id(card),
        hero_garments=_string_list(metadata.get("hero_garments")),
        secondary_garments=_string_list(metadata.get("secondary_garments")),
        core_accessories=_string_list(metadata.get("core_accessories"))
        or _string_list(metadata.get("accessories")),
        props=_string_list(metadata.get("props")),
        composition_cues=_string_list(metadata.get("composition_cues"))
        or _string_list(metadata.get("image_prompt_notes")),
        negative_constraints=_string_list(metadata.get("negative_constraints")),
    )


def _visual_language_facet(card: KnowledgeCard) -> StyleVisualLanguageFacet:
    metadata = card.metadata
    return StyleVisualLanguageFacet(
        style_id=_facet_style_id(card),
        palette=_string_list(metadata.get("palette")),
        lighting_mood=_string_list(metadata.get("lighting_mood")),
        photo_treatment=_string_list(metadata.get("photo_treatment")),
        mood_keywords=_string_list(metadata.get("mood_keywords")),
        visual_motifs=_string_list(metadata.get("visual_motifs")),
        platform_visual_cues=_string_list(metadata.get("platform_visual_cues")),
    )


def _relation_facet(card: KnowledgeCard) -> StyleRelationFacet:
    metadata = card.metadata
    return StyleRelationFacet(
        style_id=_facet_style_id(card),
        related_styles=_string_list(metadata.get("related_styles")),
        overlap_styles=_string_list(metadata.get("overlap_styles")),
        historical_relations=_dedupe(
            [
                *_string_list(metadata.get("historical_context")),
                *_string_list(metadata.get("preceded_by")),
                *_string_list(metadata.get("succeeded_by")),
                *_string_list(metadata.get("origin_regions")),
                *_string_list(metadata.get("era")),
            ]
        ),
        brands=_string_list(metadata.get("brands")),
        platforms=_string_list(metadata.get("platforms")),
    )


def _semantic_fragments(card: KnowledgeCard) -> list[StyleSemanticFragmentSummary]:
    metadata = card.metadata
    specs = (
        (
            "advice",
            [
                *_string_list(metadata.get("core_style_logic")),
                *_string_list(metadata.get("styling_rules")),
            ],
        ),
        (
            "visual_language",
            [
                *_string_list(metadata.get("palette")),
                *_string_list(metadata.get("lighting_mood")),
                *_string_list(metadata.get("photo_treatment")),
            ],
        ),
        (
            "image_composition",
            [
                *_string_list(metadata.get("hero_garments")),
                *_string_list(metadata.get("composition_cues")),
            ],
        ),
        (
            "relations",
            [
                *_string_list(metadata.get("related_styles")),
                *_string_list(metadata.get("historical_context")),
            ],
        ),
    )
    fragments: list[StyleSemanticFragmentSummary] = []
    for fragment_type, values in specs:
        summary = "; ".join(_dedupe(values)[:6])
        if not summary:
            continue
        fragments.append(
            StyleSemanticFragmentSummary(
                style_id=_facet_style_id(card),
                fragment_type=fragment_type,
                summary=summary,
                source_ref=card.source_ref,
                confidence=card.confidence,
            )
        )
    return fragments


def _has_advice(card: KnowledgeCard) -> bool:
    metadata = card.metadata
    return _has_any(
        metadata,
        "core_style_logic",
        "styling_rules",
        "casual_adaptations",
        "statement_pieces",
        "historical_notes",
        "negative_guidance",
        "styling_advice",
    )


def _has_image(card: KnowledgeCard) -> bool:
    return _has_any(
        card.metadata,
        "hero_garments",
        "secondary_garments",
        "core_accessories",
        "props",
        "composition_cues",
        "image_prompt_notes",
    )


def _has_visual(card: KnowledgeCard) -> bool:
    return _has_any(
        card.metadata,
        "palette",
        "lighting_mood",
        "photo_treatment",
        "mood_keywords",
        "visual_motifs",
        "platform_visual_cues",
    )


def _has_visual_or_image(card: KnowledgeCard) -> bool:
    return _has_visual(card) or _has_image(card)


def _has_relation(card: KnowledgeCard) -> bool:
    return _has_any(
        card.metadata,
        "related_styles",
        "overlap_styles",
        "historical_context",
        "preceded_by",
        "succeeded_by",
        "brands",
        "platforms",
        "origin_regions",
        "era",
    )


def _has_any(metadata: dict[str, Any], *keys: str) -> bool:
    return any(_string_list(metadata.get(key)) for key in keys)


def _facet_style_id(card: KnowledgeCard) -> int:
    metadata_id = card.metadata.get("style_numeric_id")
    if isinstance(metadata_id, int):
        return metadata_id
    if isinstance(metadata_id, str) and metadata_id.strip().isdigit():
        return int(metadata_id.strip())
    raw = card.style_id or card.id
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [part.strip() for part in value.replace("\n", ";").split(";")]
        return [part for part in parts if part]
    if isinstance(value, (list, tuple, set)):
        return _dedupe([str(item).strip() for item in value if str(item).strip()])
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        lowered = cleaned.lower()
        if not cleaned or lowered in seen:
            continue
        seen.add(lowered)
        result.append(cleaned)
    return result


def _string_values(*values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        for item in _string_list(value):
            if item not in result:
                result.append(item)
    return result
