from typing import Protocol

from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.reasoning import (
    FashionReasoningInput,
    FashionReasoningOutput,
    FashionReasoningPresentationPayload,
    KnowledgeContext,
    ProfileContextSnapshot,
    ProfileAlignedStyleFacetBundle,
    ReasoningRetrievalQuery,
    SessionStateSnapshot,
    StyleFacetBundle,
    StyleSemanticFragmentSummary,
    UsedStyleReference,
)
from app.domain.routing.entities.routing_decision import RoutingDecision
from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints


class RetrievalProfileSelector(Protocol):
    def select(
        self,
        *,
        routing_decision: RoutingDecision,
        session_state: SessionStateSnapshot,
        requested_profile: str | None,
    ) -> str | None:
        ...


class ReasoningKnowledgeProvider(Protocol):
    async def retrieve(self, *, query: ReasoningRetrievalQuery) -> KnowledgeContext:
        ...


class StyleFacetProvider(Protocol):
    async def load_facets(self, *, query: ReasoningRetrievalQuery) -> StyleFacetBundle:
        ...


class StyleSemanticFragmentProvider(Protocol):
    async def load_fragments(self, *, query: ReasoningRetrievalQuery) -> list[StyleSemanticFragmentSummary]:
        ...


class StyleHistoryProvider(Protocol):
    async def load_history(
        self,
        *,
        session_state: SessionStateSnapshot,
        query: ReasoningRetrievalQuery,
    ) -> list[UsedStyleReference]:
        ...


class DiversityConstraintsProvider(Protocol):
    async def build_constraints(
        self,
        *,
        session_state: SessionStateSnapshot,
        query: ReasoningRetrievalQuery,
        style_history: list[UsedStyleReference],
        style_facets: StyleFacetBundle,
    ) -> DiversityConstraints | None:
        ...


class FashionReasoningContextAssembler(Protocol):
    async def assemble(
        self,
        *,
        routing_decision: RoutingDecision,
        session_state: SessionStateSnapshot,
        profile_context: ProfileContextSnapshot | None,
        retrieval_profile: str | None,
    ) -> FashionReasoningInput:
        ...


class ProfileStyleAlignmentService(Protocol):
    async def align(
        self,
        *,
        profile: ProfileContextSnapshot,
        style_facets: StyleFacetBundle,
    ) -> ProfileAlignedStyleFacetBundle:
        ...


class FashionReasoner(Protocol):
    async def reason(self, reasoning_input: FashionReasoningInput) -> FashionReasoningOutput:
        ...


class FashionBriefBuilder(Protocol):
    async def build(
        self,
        *,
        reasoning_input: FashionReasoningInput,
        reasoning_output: FashionReasoningOutput,
    ) -> FashionBrief:
        ...


class FashionReasoningPipeline(Protocol):
    async def run(
        self,
        *,
        routing_decision: RoutingDecision,
        session_state: SessionStateSnapshot,
        profile_context: ProfileContextSnapshot | None,
        retrieval_profile: str | None,
    ) -> FashionReasoningOutput:
        ...


class ReasoningOutputMapper(Protocol):
    def to_presentation(self, reasoning_output: FashionReasoningOutput) -> FashionReasoningPresentationPayload:
        ...
