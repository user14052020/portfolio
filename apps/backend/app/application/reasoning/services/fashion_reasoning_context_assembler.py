import hashlib
from typing import Any

from app.application.knowledge.contracts import KnowledgeContextAssembler as RuntimeKnowledgeContextAssembler
from app.application.knowledge.contracts import KnowledgeRuntimeSettingsProvider
from app.application.reasoning.contracts import (
    DiversityConstraintsProvider,
    ReasoningKnowledgeProvider,
    RetrievalProfileSelector,
    StyleFacetProvider,
    StyleHistoryProvider,
    StyleSemanticFragmentProvider,
)
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery, KnowledgeRuntimeFlags
from app.domain.knowledge.enums import KnowledgeType
from app.application.reasoning.services.retrieval_profile_selector import DefaultRetrievalProfileSelector
from app.domain.reasoning import (
    FashionReasoningInput,
    KnowledgeContext,
    ProfileContextSnapshot,
    ReasoningRetrievalQuery,
    SessionStateSnapshot,
    StyleFacetBundle,
    StyleSemanticFragmentSummary,
    UsedStyleReference,
    StyleAdviceFacet,
    StyleImageFacet,
    StyleRelationFacet,
    StyleVisualLanguageFacet,
)
from app.domain.routing.entities.routing_decision import RoutingDecision
from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints


class EmptyReasoningKnowledgeProvider:
    async def retrieve(self, *, query: ReasoningRetrievalQuery) -> KnowledgeContext:
        return KnowledgeContext()


class EmptyStyleFacetProvider:
    async def load_facets(self, *, query: ReasoningRetrievalQuery) -> StyleFacetBundle:
        return StyleFacetBundle()


class EmptyStyleSemanticFragmentProvider:
    async def load_fragments(self, *, query: ReasoningRetrievalQuery) -> list[StyleSemanticFragmentSummary]:
        return []


class SessionStateStyleHistoryProvider:
    async def load_history(
        self,
        *,
        session_state: SessionStateSnapshot,
        query: ReasoningRetrievalQuery,
    ) -> list[UsedStyleReference]:
        return [item.model_copy(deep=True) for item in session_state.style_history]


class NoopDiversityConstraintsProvider:
    async def build_constraints(
        self,
        *,
        session_state: SessionStateSnapshot,
        query: ReasoningRetrievalQuery,
        style_history: list[UsedStyleReference],
        style_facets: StyleFacetBundle,
    ) -> DiversityConstraints | None:
        return None


class RecentStyleDiversityConstraintsProvider:
    async def build_constraints(
        self,
        *,
        session_state: SessionStateSnapshot,
        query: ReasoningRetrievalQuery,
        style_history: list[UsedStyleReference],
        style_facets: StyleFacetBundle,
    ) -> DiversityConstraints | None:
        if session_state.diversity_constraints is not None:
            return session_state.diversity_constraints.model_copy(deep=True)

        recent_history = style_history[-5:]
        if not recent_history:
            return None
        return DiversityConstraints(
            avoid_silhouette_families=_unique(
                style.silhouette_family
                for style in recent_history
                if style.silhouette_family
            ),
            avoid_palette=_unique(
                color
                for style in recent_history
                for color in style.palette
            ),
            avoid_hero_garments=_unique(
                garment
                for style in recent_history
                for garment in style.hero_garments
            ),
            force_material_contrast=bool(style_facets.image_facets),
            force_accessory_change=bool(style_facets.image_facets),
            force_visual_preset_shift=query.retrieval_profile == "visual_heavy",
            target_semantic_distance="medium",
            target_visual_distance="high" if query.retrieval_profile == "visual_heavy" else "medium",
        )


class DefaultFashionReasoningContextAssembler:
    def __init__(
        self,
        *,
        knowledge_provider: ReasoningKnowledgeProvider | None = None,
        style_facet_provider: StyleFacetProvider | None = None,
        style_history_provider: StyleHistoryProvider | None = None,
        diversity_constraints_provider: DiversityConstraintsProvider | None = None,
        semantic_fragment_provider: StyleSemanticFragmentProvider | None = None,
        retrieval_profile_selector: RetrievalProfileSelector | None = None,
        knowledge_context_assembler: RuntimeKnowledgeContextAssembler | None = None,
        knowledge_runtime_flags: KnowledgeRuntimeFlags | None = None,
        knowledge_runtime_settings_provider: KnowledgeRuntimeSettingsProvider | None = None,
    ) -> None:
        self._knowledge_provider = knowledge_provider or EmptyReasoningKnowledgeProvider()
        self._style_facet_provider = style_facet_provider or EmptyStyleFacetProvider()
        self._style_history_provider = style_history_provider or SessionStateStyleHistoryProvider()
        self._diversity_constraints_provider = (
            diversity_constraints_provider or RecentStyleDiversityConstraintsProvider()
        )
        self._semantic_fragment_provider = semantic_fragment_provider or EmptyStyleSemanticFragmentProvider()
        self._retrieval_profile_selector = retrieval_profile_selector or DefaultRetrievalProfileSelector()
        self._knowledge_context_assembler = knowledge_context_assembler
        self._knowledge_runtime_flags = knowledge_runtime_flags or KnowledgeRuntimeFlags()
        self._knowledge_runtime_settings_provider = knowledge_runtime_settings_provider

    async def assemble(
        self,
        *,
        routing_decision: RoutingDecision,
        session_state: SessionStateSnapshot,
        profile_context: ProfileContextSnapshot | None,
        retrieval_profile: str | None,
    ) -> FashionReasoningInput:
        selected_profile = self._retrieval_profile_selector.select(
            routing_decision=routing_decision,
            session_state=session_state,
            requested_profile=retrieval_profile or routing_decision.retrieval_profile,
        )
        mode = routing_decision.mode.value
        query = ReasoningRetrievalQuery.from_pipeline_inputs(
            mode=mode,
            session_state=session_state,
            profile_context=profile_context,
            retrieval_profile=selected_profile,
            generation_intent=routing_decision.generation_intent,
        )

        knowledge_context, style_facets, semantic_fragments = await self._knowledge_runtime_inputs(query=query)
        style_history = await self._style_history_provider.load_history(
            session_state=session_state,
            query=query,
        )
        knowledge_context = _with_style_history_cards(
            knowledge_context=knowledge_context,
            style_history=style_history,
        )
        diversity_constraints = await self._diversity_constraints_provider.build_constraints(
            session_state=session_state,
            query=query,
            style_history=style_history,
            style_facets=style_facets,
        )

        return FashionReasoningInput(
            mode=mode,
            user_request=session_state.user_request,
            recent_conversation_summary=session_state.recent_conversation_summary,
            profile_context=profile_context,
            style_history=style_history,
            diversity_constraints=diversity_constraints,
            active_slots=dict(session_state.active_slots),
            knowledge_context=knowledge_context,
            generation_intent=routing_decision.generation_intent,
            visual_intent_signal=query.visual_intent_signal,
            visual_intent_required=query.visual_intent_required,
            can_generate_now=session_state.can_generate_now,
            retrieval_profile=selected_profile,
            style_context=knowledge_context.style_cards,
            style_advice_facets=style_facets.advice_facets,
            style_image_facets=style_facets.image_facets,
            style_visual_language_facets=style_facets.visual_language_facets,
            style_relation_facets=style_facets.relation_facets,
            style_semantic_fragments=semantic_fragments,
        )

    async def _knowledge_runtime_inputs(
        self,
        *,
        query: ReasoningRetrievalQuery,
    ) -> tuple[KnowledgeContext, StyleFacetBundle, list[StyleSemanticFragmentSummary]]:
        runtime_flags = await self._resolved_runtime_flags()
        if self._knowledge_context_assembler is None:
            knowledge_context = _filter_knowledge_context_for_runtime_flags(
                await self._knowledge_provider.retrieve(query=query),
                runtime_flags,
            )
            style_facets = _filter_style_facets_for_runtime_flags(
                await self._style_facet_provider.load_facets(query=query),
                runtime_flags,
            )
            semantic_fragments = _filter_semantic_fragments_for_runtime_flags(
                await self._semantic_fragment_provider.load_fragments(query=query),
                runtime_flags,
            )
            return knowledge_context, style_facets, semantic_fragments

        knowledge_context = await self._knowledge_context_assembler.assemble(
            _knowledge_query(
                query=query,
                runtime_flags=runtime_flags,
            )
        )
        knowledge_context = _filter_knowledge_context_for_runtime_flags(
            knowledge_context,
            runtime_flags,
        )
        style_facets = _filter_style_facets_for_runtime_flags(
            _style_facets_from_knowledge_context(knowledge_context),
            runtime_flags,
        )
        semantic_fragments = _filter_semantic_fragments_for_runtime_flags(
            _semantic_fragments_from_knowledge_context(knowledge_context),
            runtime_flags,
        )
        return knowledge_context, style_facets, semantic_fragments

    async def _resolved_runtime_flags(self) -> KnowledgeRuntimeFlags:
        if self._knowledge_runtime_settings_provider is None:
            return self._knowledge_runtime_flags
        return await self._knowledge_runtime_settings_provider.get_runtime_flags()


def _unique(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip() if isinstance(value, str) else ""
        lowered = cleaned.lower()
        if not cleaned or lowered in seen:
            continue
        seen.add(lowered)
        result.append(cleaned)
    return result


def _with_style_history_cards(
    *,
    knowledge_context: KnowledgeContext,
    style_history: list[UsedStyleReference],
) -> KnowledgeContext:
    if not style_history:
        return knowledge_context

    history_cards = [
        KnowledgeCard(
            id=f"style_history:{item.style_id or item.style_name or index}",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            title=item.style_name or item.style_cluster or f"Style history {index}",
            summary=_style_history_summary(item),
            style_id=str(item.style_id) if item.style_id is not None else None,
            metadata={
                "style_cluster": item.style_cluster,
                "silhouette_family": item.silhouette_family,
                "palette": list(item.palette),
                "hero_garments": list(item.hero_garments),
                "visual_motifs": list(item.visual_motifs),
                "source": "style_history",
            },
        )
        for index, item in enumerate(style_history, start=1)
    ]
    return knowledge_context.model_copy(
        update={
            "style_history_cards": [
                *knowledge_context.style_history_cards,
                *history_cards,
            ]
        },
        deep=True,
    )


def _style_history_summary(item: UsedStyleReference) -> str:
    bits = [
        item.style_cluster or "",
        item.silhouette_family or "",
        ", ".join(item.palette),
        ", ".join(item.hero_garments),
        ", ".join(item.visual_motifs),
    ]
    summary = " | ".join(bit for bit in bits if bit)
    return summary or "Previously used style reference."


def _knowledge_query(
    *,
    query: ReasoningRetrievalQuery,
    runtime_flags: KnowledgeRuntimeFlags,
) -> KnowledgeQuery:
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
        limit=_limit_for_profile(query.retrieval_profile, 8),
        message=query.user_request,
        user_request=query.user_request,
        profile_context=query.profile_context.values if query.profile_context is not None else {},
        retrieval_profile=query.retrieval_profile,
        need_visual_knowledge=query.generation_intent or query.mode in {"visual_offer", "style_exploration"},
        need_historical_knowledge=(
            runtime_flags.use_historical_context
            and query.mode in {"general_advice", "style_exploration", "occasion_outfit"}
        ),
        need_styling_rules=query.mode in {"style_exploration", "occasion_outfit", "garment_matching"},
        need_color_poetics=(
            runtime_flags.use_color_poetics
            and (query.generation_intent or query.mode in {"style_exploration", "general_advice"})
        ),
    )


def _style_facets_from_knowledge_context(knowledge_context: KnowledgeContext) -> StyleFacetBundle:
    cards = _unique_knowledge_cards(knowledge_context)
    return StyleFacetBundle(
        advice_facets=[_advice_facet(card) for card in cards if _has_advice(card)],
        image_facets=[_image_facet(card) for card in cards if _has_image(card)],
        visual_language_facets=[_visual_language_facet(card) for card in cards if _has_visual(card)],
        relation_facets=[_relation_facet(card) for card in cards if _has_relation(card)],
    )


def _semantic_fragments_from_knowledge_context(
    knowledge_context: KnowledgeContext,
) -> list[StyleSemanticFragmentSummary]:
    fragments: list[StyleSemanticFragmentSummary] = []
    for card in _unique_knowledge_cards(knowledge_context):
        fragments.extend(_semantic_fragments(card))
    return fragments


def _unique_knowledge_cards(knowledge_context: KnowledgeContext) -> list[KnowledgeCard]:
    seen_ids: set[str] = set()
    cards: list[KnowledgeCard] = []
    for bucket in (
        knowledge_context.knowledge_cards,
        knowledge_context.style_advice_cards,
        knowledge_context.style_visual_cards,
        knowledge_context.style_history_cards,
        knowledge_context.editorial_cards,
    ):
        for card in bucket:
            if card.id in seen_ids:
                continue
            seen_ids.add(card.id)
            cards.append(card)
    return cards


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


def _filter_knowledge_context_for_runtime_flags(
    knowledge_context: KnowledgeContext,
    runtime_flags: KnowledgeRuntimeFlags,
) -> KnowledgeContext:
    filtered = knowledge_context.model_copy(deep=True)
    if not runtime_flags.use_editorial_knowledge:
        filtered.editorial_cards = []
    if not runtime_flags.use_historical_context:
        filtered.knowledge_cards = [
            card
            for card in filtered.knowledge_cards
            if card.knowledge_type not in _STRICT_HISTORICAL_KNOWLEDGE_TYPES
        ]
        filtered.style_history_cards = [
            card
            for card in filtered.style_history_cards
            if card.knowledge_type not in _STRICT_HISTORICAL_KNOWLEDGE_TYPES
        ]
    if not runtime_flags.use_color_poetics:
        filtered.knowledge_cards = [
            card
            for card in filtered.knowledge_cards
            if card.knowledge_type not in _COLOR_POETIC_KNOWLEDGE_TYPES
        ]
        filtered.style_visual_cards = [
            card
            for card in filtered.style_visual_cards
            if card.knowledge_type not in _COLOR_POETIC_KNOWLEDGE_TYPES
        ]
    return filtered


def _filter_style_facets_for_runtime_flags(
    style_facets: StyleFacetBundle,
    runtime_flags: KnowledgeRuntimeFlags,
) -> StyleFacetBundle:
    filtered = style_facets.model_copy(deep=True)
    if not runtime_flags.use_historical_context:
        filtered.advice_facets = [
            facet.model_copy(update={"historical_notes": []}, deep=True)
            for facet in filtered.advice_facets
        ]
    if not runtime_flags.use_color_poetics:
        filtered.visual_language_facets = [
            facet.model_copy(
                update={
                    "palette": [],
                    "lighting_mood": [],
                    "photo_treatment": [],
                },
                deep=True,
            )
            for facet in filtered.visual_language_facets
        ]
    return filtered


def _filter_semantic_fragments_for_runtime_flags(
    semantic_fragments: list[StyleSemanticFragmentSummary],
    runtime_flags: KnowledgeRuntimeFlags,
) -> list[StyleSemanticFragmentSummary]:
    filtered = list(semantic_fragments)
    if not runtime_flags.use_historical_context:
        filtered = [
            fragment
            for fragment in filtered
            if fragment.fragment_type.strip().lower() not in {"relations", "history", "historical"}
        ]
    if not runtime_flags.use_color_poetics:
        filtered = [
            fragment
            for fragment in filtered
            if fragment.fragment_type.strip().lower() not in {"visual_language"}
        ]
    return filtered


_STRICT_HISTORICAL_KNOWLEDGE_TYPES = {
    KnowledgeType.FASHION_HISTORY,
    KnowledgeType.STYLE_HISTORY,
}

_COLOR_POETIC_KNOWLEDGE_TYPES = {
    KnowledgeType.COLOR_THEORY,
    KnowledgeType.COMPOSITION_THEORY,
    KnowledgeType.LIGHT_THEORY,
    KnowledgeType.STYLE_PALETTE_LOGIC,
    KnowledgeType.STYLE_PHOTO_TREATMENT,
}
