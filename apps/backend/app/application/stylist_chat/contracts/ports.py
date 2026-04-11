from dataclasses import dataclass, field
from typing import Any, Protocol

from app.domain.chat_context import ChatModeContext, GenerationIntent, StyleDirectionContext
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment
from app.domain.garment_matching.entities.garment_matching_outfit_brief import GarmentMatchingOutfitBrief
from app.domain.garment_matching.policies.garment_completeness_policy import GarmentCompletenessAssessment
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext
from app.domain.occasion_outfit.entities.occasion_outfit_brief import OccasionOutfitBrief
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessAssessment
from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints
from app.domain.style_exploration.entities.style_direction import StyleDirection
from app.domain.style_exploration.entities.style_exploration_brief import StyleExplorationBrief
from app.services.chat_mode_resolver import ModeResolution


class LLMReasonerError(RuntimeError):
    pass


class LLMReasonerContextLimitError(LLMReasonerError):
    pass


@dataclass(slots=True)
class ReasoningOutput:
    reply_text: str
    image_brief_en: str
    route: str
    provider: str
    raw_content: str = ""
    reasoning_mode: str = "primary"


@dataclass(slots=True)
class OccasionExtractionOutput:
    event_type: str | None = None
    venue: str | None = None
    dress_code: str | None = None
    time_of_day: str | None = None
    season_or_weather: str | None = None
    desired_impression: str | None = None
    provider: str = "deterministic"
    raw_content: str = ""


@dataclass(slots=True)
class KnowledgeItem:
    key: str
    text: str


@dataclass(slots=True)
class KnowledgeResult:
    items: list[KnowledgeItem] = field(default_factory=list)
    source: str = "none"
    query: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GenerationScheduleRequest:
    session_id: str
    locale: str
    input_text: str
    recommendation_text: str
    prompt: str
    input_asset_id: int | None
    profile_context: dict[str, str | int | None]
    generation_intent: GenerationIntent | None
    idempotency_key: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GenerationScheduleResult:
    job_id: str | None
    status: str
    job: Any | None = None
    blocked_by_active_job: bool = False
    notice_text: str | None = None


class ChatContextStorePort(Protocol):
    async def load(self, session_id: str) -> tuple[Any | None, ChatModeContext]:
        ...

    async def save(
        self,
        *,
        session_id: str,
        context: ChatModeContext,
        record: Any | None,
    ) -> Any:
        ...


class ModeResolverPort(Protocol):
    def resolve(
        self,
        *,
        context: ChatModeContext,
        requested_intent: Any,
        command_name: str | None,
        command_step: str | None,
        metadata: dict[str, Any] | None,
    ) -> ModeResolution:
        ...


class LLMReasoner(Protocol):
    async def decide(self, *, locale: str, reasoning_input: dict[str, Any]) -> ReasoningOutput:
        ...

    async def extract_occasion_slots(
        self,
        *,
        locale: str,
        user_message: str,
        conversation_history: list[dict[str, str]],
        existing_slots: dict[str, str | None],
    ) -> OccasionExtractionOutput:
        ...


class FallbackReasonerStrategy(Protocol):
    async def decide(self, *, locale: str, reasoning_input: dict[str, Any]) -> ReasoningOutput:
        ...


class PromptBuilder(Protocol):
    async def build(self, *, brief: dict[str, Any]) -> dict[str, Any]:
        ...


class GarmentExtractor(Protocol):
    async def extract(
        self,
        user_text: str,
        asset_id: str | None = None,
        existing_anchor: AnchorGarment | None = None,
    ) -> AnchorGarment:
        ...


class GarmentCompletenessEvaluator(Protocol):
    def evaluate(self, garment: AnchorGarment) -> GarmentCompletenessAssessment:
        ...


class OccasionContextExtractor(Protocol):
    async def extract(
        self,
        *,
        locale: str,
        user_message: str,
        context: ChatModeContext,
        existing_context: OccasionContext | None,
        asset_metadata: dict[str, Any] | None = None,
        fallback_history: list[dict[str, str]] | None = None,
    ) -> OccasionContext:
        ...


class OccasionCompletenessEvaluator(Protocol):
    def evaluate(self, context: OccasionContext) -> OccasionCompletenessAssessment:
        ...


class OccasionClarificationSelector(Protocol):
    def build(
        self,
        *,
        locale: str,
        context: OccasionContext,
        assessment: OccasionCompletenessAssessment,
    ) -> tuple[Any, str]:
        ...


class KnowledgeProvider(Protocol):
    async def fetch(self, *, query: dict[str, Any]) -> KnowledgeResult:
        ...


class GarmentKnowledgeProvider(Protocol):
    async def fetch_for_anchor_garment(
        self,
        garment: AnchorGarment,
        context: dict[str, Any] | None = None,
    ) -> KnowledgeResult:
        ...


class OccasionKnowledgeProvider(Protocol):
    async def fetch_for_occasion(
        self,
        context: OccasionContext,
        profile_context: dict[str, Any] | None = None,
    ) -> KnowledgeResult:
        ...


class OutfitBriefBuilder(Protocol):
    async def build(
        self,
        garment: AnchorGarment,
        context: dict[str, Any],
        knowledge_result: KnowledgeResult,
    ) -> GarmentMatchingOutfitBrief:
        ...


class OccasionOutfitBriefBuilder(Protocol):
    async def build(
        self,
        occasion_context: OccasionContext,
        context: dict[str, Any],
        knowledge_result: KnowledgeResult,
    ) -> OccasionOutfitBrief:
        ...


class StyleHistoryProvider(Protocol):
    async def get_recent(self, session_id: str) -> list[StyleDirectionContext]:
        ...

    async def pick_next(
        self,
        *,
        session_id: str,
        style_history: list[StyleDirectionContext],
    ) -> tuple[StyleDirectionContext, Any | None]:
        ...

    async def record_exposure(self, *, session_id: str, style_direction: Any) -> None:
        ...


class CandidateStyleSelector(Protocol):
    async def select(
        self,
        *,
        session_id: str,
        style_history: list[StyleDirection],
    ) -> tuple[StyleDirection, Any | None]:
        ...


class SemanticDiversityBuilder(Protocol):
    def build(
        self,
        *,
        history: list[StyleDirection],
        candidate_style: StyleDirection,
        session_context: dict[str, Any] | None = None,
    ) -> DiversityConstraints:
        ...


class VisualDiversityBuilder(Protocol):
    def build(
        self,
        *,
        history: list[StyleDirection],
        current_visual_presets: list[dict[str, Any]] | None = None,
    ) -> DiversityConstraints:
        ...


class StyleExplorationBriefBuilder(Protocol):
    async def build(
        self,
        *,
        style_direction: StyleDirection,
        history: list[StyleDirection],
        diversity_constraints: DiversityConstraints,
    ) -> StyleExplorationBrief:
        ...


class GenerationJobScheduler(Protocol):
    async def sync_context(self, context: ChatModeContext) -> ChatModeContext:
        ...

    async def enqueue(self, request: GenerationScheduleRequest) -> GenerationScheduleResult:
        ...


class EventLogger(Protocol):
    async def emit(self, event_name: str, payload: dict[str, Any]) -> None:
        ...


class MetricsRecorder(Protocol):
    async def increment(
        self,
        metric_name: str,
        *,
        value: int = 1,
        tags: dict[str, Any] | None = None,
    ) -> None:
        ...

    async def observe(
        self,
        metric_name: str,
        *,
        value: float,
        tags: dict[str, Any] | None = None,
    ) -> None:
        ...


class ContextCheckpointWriter(Protocol):
    async def save_checkpoint(self, *, session_id: str, context: ChatModeContext) -> None:
        ...
