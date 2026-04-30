from typing import Any, Protocol

from app.application.reasoning.profile_context_models import ProfileContextInput, ProfileContextUpdate
from app.domain.knowledge.entities import KnowledgeRuntimeFlags
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.reasoning import (
    FashionReasoningInput,
    FashionReasoningOutput,
    FashionReasoningPresentationPayload,
    KnowledgeContext,
    ProfileClarificationDecision,
    ProfileContext,
    ProfileContextSnapshot,
    ProfileAlignedStyleFacetBundle,
    ReasoningRetrievalQuery,
    SessionStateSnapshot,
    StyleFacetBundle,
    StyleSemanticFragmentSummary,
    StyledAnswer,
    UsedStyleReference,
    VoiceCompositionDraft,
    VoiceContext,
    VoiceLayerReasoningPayload,
    VoicePrompt,
    VoiceRuntimeFlags,
    VoiceToneDecision,
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


class ProfileContextNormalizer(Protocol):
    def normalize(
        self,
        profile: ProfileContext | ProfileContextSnapshot | ProfileContextUpdate | dict[str, Any] | None,
    ) -> ProfileContext:
        ...

    def snapshot(
        self,
        profile: ProfileContext | ProfileContextSnapshot | ProfileContextUpdate | dict[str, Any] | None,
        *,
        source: str = "runtime",
    ) -> ProfileContextSnapshot:
        ...


class ProfileContextService(Protocol):
    async def build_context(self, request: ProfileContextInput) -> ProfileContext:
        ...

    async def build_snapshot(self, request: ProfileContextInput) -> ProfileContextSnapshot:
        ...

    async def merge_updates(
        self,
        current: ProfileContext,
        updates: ProfileContextUpdate,
    ) -> ProfileContext:
        ...

    async def snapshot(
        self,
        profile: ProfileContext | ProfileContextSnapshot | dict[str, Any] | None,
    ) -> ProfileContextSnapshot:
        ...


class ProfileClarificationPolicy(Protocol):
    async def evaluate(
        self,
        *,
        mode: str,
        profile: ProfileContextSnapshot | None,
        style_bundle: StyleFacetBundle | None,
    ) -> ProfileClarificationDecision:
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


class VoiceTonePolicy(Protocol):
    async def resolve(self, context: VoiceContext) -> VoiceToneDecision:
        ...


class VoiceRuntimeSettingsProvider(Protocol):
    async def get_runtime_flags(self) -> VoiceRuntimeFlags:
        ...


class VoicePromptBuilder(Protocol):
    async def build(
        self,
        reasoning_output: FashionReasoningOutput,
        context: VoiceContext,
        tone_decision: VoiceToneDecision,
    ) -> VoicePrompt:
        ...


class VoiceCompositionClient(Protocol):
    async def compose(
        self,
        *,
        prompt: VoicePrompt,
        context: VoiceContext,
    ) -> VoiceCompositionDraft:
        ...


class VoiceLayerComposer(Protocol):
    async def compose(
        self,
        reasoning_output: FashionReasoningOutput,
        context: VoiceContext,
        runtime_flags: KnowledgeRuntimeFlags | None = None,
    ) -> StyledAnswer:
        ...


class ReasoningOutputMapper(Protocol):
    async def to_presentation(
        self,
        reasoning_output: FashionReasoningOutput,
        *,
        voice_context: VoiceContext | None = None,
        runtime_flags: KnowledgeRuntimeFlags | None = None,
    ) -> FashionReasoningPresentationPayload:
        ...
