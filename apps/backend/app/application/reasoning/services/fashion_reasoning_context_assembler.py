from app.application.reasoning.contracts import (
    DiversityConstraintsProvider,
    ReasoningKnowledgeProvider,
    RetrievalProfileSelector,
    StyleFacetProvider,
    StyleHistoryProvider,
    StyleSemanticFragmentProvider,
)
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
    ) -> None:
        self._knowledge_provider = knowledge_provider or EmptyReasoningKnowledgeProvider()
        self._style_facet_provider = style_facet_provider or EmptyStyleFacetProvider()
        self._style_history_provider = style_history_provider or SessionStateStyleHistoryProvider()
        self._diversity_constraints_provider = (
            diversity_constraints_provider or RecentStyleDiversityConstraintsProvider()
        )
        self._semantic_fragment_provider = semantic_fragment_provider or EmptyStyleSemanticFragmentProvider()
        self._retrieval_profile_selector = retrieval_profile_selector or DefaultRetrievalProfileSelector()

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

        knowledge_context = await self._knowledge_provider.retrieve(query=query)
        style_facets = await self._style_facet_provider.load_facets(query=query)
        style_history = await self._style_history_provider.load_history(
            session_state=session_state,
            query=query,
        )
        diversity_constraints = await self._diversity_constraints_provider.build_constraints(
            session_state=session_state,
            query=query,
            style_history=style_history,
            style_facets=style_facets,
        )
        semantic_fragments = await self._semantic_fragment_provider.load_fragments(query=query)

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
            can_generate_now=session_state.can_generate_now,
            retrieval_profile=selected_profile,
            style_context=knowledge_context.style_cards,
            style_advice_facets=style_facets.advice_facets,
            style_image_facets=style_facets.image_facets,
            style_visual_language_facets=style_facets.visual_language_facets,
            style_relation_facets=style_facets.relation_facets,
            style_semantic_fragments=semantic_fragments,
        )


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
