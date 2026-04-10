import unittest
from types import SimpleNamespace

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import (
    GenerationScheduleRequest,
    GenerationScheduleResult,
    KnowledgeItem,
    KnowledgeResult,
    LLMReasonerContextLimitError,
    LLMReasonerError,
    OccasionExtractionOutput,
    ReasoningOutput,
)
from app.application.stylist_chat.handlers.garment_matching_handler import GarmentMatchingHandler
from app.application.stylist_chat.handlers.general_advice_handler import GeneralAdviceHandler
from app.application.stylist_chat.handlers.occasion_outfit_handler import OccasionOutfitHandler
from app.application.stylist_chat.handlers.style_exploration_handler import StyleExplorationHandler
from app.application.stylist_chat.orchestrator.command_dispatcher import CommandDispatcher
from app.application.stylist_chat.orchestrator.mode_router import ModeRouter
from app.application.stylist_chat.orchestrator.stylist_chat_orchestrator import StylistChatOrchestrator
from app.application.stylist_chat.results.decision_result import DecisionType
from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder
from app.application.stylist_chat.services.diversity_constraints_builder import DiversityConstraintsBuilder
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.application.stylist_chat.services.reasoning_context_builder import ReasoningContextBuilder
from app.domain.chat_context import ChatModeContext, StyleDirectionContext
from app.domain.chat_modes import ChatMode, FlowState
from app.models.enums import GenerationStatus
from app.services.chat_mode_resolver import chat_mode_resolver


class FakeContextStore:
    def __init__(self) -> None:
        self.record = object()
        self.context = ChatModeContext()
        self.saved_contexts: list[ChatModeContext] = []

    async def load(self, session_id: str):
        return self.record, self.context.model_copy(deep=True)

    async def save(self, *, session_id: str, context: ChatModeContext, record):
        self.context = context.model_copy(deep=True)
        self.saved_contexts.append(self.context.model_copy(deep=True))
        return self.record


class FakeModeResolver:
    def resolve(self, **kwargs):
        return chat_mode_resolver.resolve(**kwargs)


class FakeReasoner:
    def __init__(self) -> None:
        self.reply_text = "Mock stylist reply"
        self.image_brief = "cohesive editorial flat lay outfit"
        self.route = "text_only"
        self.raise_error = False
        self.raise_context_limit = False
        self.occasion_output = OccasionExtractionOutput()
        self.last_reasoning_input: dict[str, object] | None = None

    async def decide(self, *, locale: str, reasoning_input: dict[str, object]) -> ReasoningOutput:
        self.last_reasoning_input = reasoning_input
        if self.raise_context_limit:
            raise LLMReasonerContextLimitError("context limit")
        if self.raise_error:
            raise LLMReasonerError("provider unavailable")
        return ReasoningOutput(
            reply_text=self.reply_text,
            image_brief_en=self.image_brief,
            route=self.route,
            provider="fake-vllm",
            reasoning_mode="primary",
        )

    async def extract_occasion_slots(
        self,
        *,
        locale: str,
        user_message: str,
        conversation_history: list[dict[str, str]],
        existing_slots: dict[str, str | None],
    ) -> OccasionExtractionOutput:
        return self.occasion_output


class FakeFallbackReasoner:
    async def decide(self, *, locale: str, reasoning_input: dict[str, object]) -> ReasoningOutput:
        return ReasoningOutput(
            reply_text="Fallback reply" if locale == "en" else "Резервный ответ",
            image_brief_en="fallback editorial flat lay outfit",
            route="text_and_generation",
            provider="fake-fallback",
            reasoning_mode="fallback",
        )


class FakeKnowledgeProvider:
    async def fetch(self, *, query: dict[str, object]) -> KnowledgeResult:
        return KnowledgeResult(
            items=[KnowledgeItem("rule", "Keep the outfit coherent."), KnowledgeItem("fit", "Balance proportions.")],
            source="test",
            query=query,
        )


class FakePromptBuilder:
    async def build(self, *, brief: dict[str, object]) -> dict[str, object]:
        return {
            "prompt": f"prompt::{brief.get('image_brief_en', '')}",
            "image_brief_en": brief.get("image_brief_en", ""),
            "recommendation_text": brief.get("recommendation_text", ""),
            "input_asset_id": brief.get("asset_id"),
        }


class FakeStyleHistoryProvider:
    def __init__(self) -> None:
        self.styles = [
            StyleDirectionContext(
                style_id="artful-minimalism",
                style_name="Artful Minimalism",
                palette=["chalk", "charcoal"],
                silhouette="clean and elongated",
                hero_garments=["structured coat"],
                styling_mood="quiet and precise",
                composition_type="editorial flat lay",
            ),
            StyleDirectionContext(
                style_id="soft-retro-prep",
                style_name="Soft Retro Prep",
                palette=["camel", "cream"],
                silhouette="relaxed collegiate layering",
                hero_garments=["oxford shirt"],
                styling_mood="polished but warm",
                composition_type="editorial flat lay",
            ),
        ]
        self.index = 0

    async def get_recent(self, session_id: str):
        return []

    async def pick_next(self, *, session_id: str, style_history: list[StyleDirectionContext]):
        style = self.styles[self.index % len(self.styles)]
        self.index += 1
        return style, None

    async def record_exposure(self, *, session_id: str, style_direction) -> None:
        return None


class FakeGenerationScheduler:
    def __init__(self) -> None:
        self.enqueued: list[GenerationScheduleRequest] = []
        self.block_active = False

    async def sync_context(self, context: ChatModeContext) -> ChatModeContext:
        if context.current_job_id and context.flow_state == FlowState.READY_FOR_GENERATION:
            context.flow_state = FlowState.GENERATION_QUEUED
        return context

    async def enqueue(self, request: GenerationScheduleRequest) -> GenerationScheduleResult:
        if self.block_active:
            return GenerationScheduleResult(
                job_id="job-active",
                status=GenerationStatus.RUNNING.value,
                job=SimpleNamespace(id=99, public_id="job-active", status=GenerationStatus.RUNNING),
                blocked_by_active_job=True,
            )
        self.enqueued.append(request)
        job_id = f"job-{len(self.enqueued)}"
        return GenerationScheduleResult(
            job_id=job_id,
            status=GenerationStatus.PENDING.value,
            job=SimpleNamespace(id=len(self.enqueued), public_id=job_id, status=GenerationStatus.PENDING),
        )


class FakeEventLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    async def emit(self, event_name: str, payload: dict[str, object]) -> None:
        self.events.append((event_name, payload))


def build_test_orchestrator():
    context_store = FakeContextStore()
    mode_resolver = FakeModeResolver()
    reasoner = FakeReasoner()
    fallback_reasoner = FakeFallbackReasoner()
    knowledge_provider = FakeKnowledgeProvider()
    style_history_provider = FakeStyleHistoryProvider()
    generation_scheduler = FakeGenerationScheduler()
    event_logger = FakeEventLogger()

    reasoning_context_builder = ReasoningContextBuilder()
    generation_request_builder = GenerationRequestBuilder(prompt_builder=FakePromptBuilder())
    clarification_builder = ClarificationMessageBuilder()
    diversity_constraints_builder = DiversityConstraintsBuilder()
    shared_kwargs = {
        "reasoner": reasoner,
        "fallback_reasoner": fallback_reasoner,
        "knowledge_provider": knowledge_provider,
        "reasoning_context_builder": reasoning_context_builder,
        "generation_request_builder": generation_request_builder,
    }
    handlers = {
        ChatMode.GENERAL_ADVICE: GeneralAdviceHandler(**shared_kwargs),
        ChatMode.GARMENT_MATCHING: GarmentMatchingHandler(
            clarification_builder=clarification_builder,
            **shared_kwargs,
        ),
        ChatMode.OCCASION_OUTFIT: OccasionOutfitHandler(
            clarification_builder=clarification_builder,
            **shared_kwargs,
        ),
        ChatMode.STYLE_EXPLORATION: StyleExplorationHandler(
            style_history_provider=style_history_provider,
            diversity_constraints_builder=diversity_constraints_builder,
            **shared_kwargs,
        ),
    }
    orchestrator = StylistChatOrchestrator(
        context_store=context_store,
        generation_scheduler=generation_scheduler,
        event_logger=event_logger,
        command_dispatcher=CommandDispatcher(mode_resolver=mode_resolver),
        mode_router=ModeRouter(handlers=handlers),
        generation_request_builder=generation_request_builder,
    )
    return (
        orchestrator,
        context_store,
        reasoner,
        generation_scheduler,
        event_logger,
    )


class StylistOrchestratorScenarioTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        (
            self.orchestrator,
            self.context_store,
            self.reasoner,
            self.scheduler,
            self.event_logger,
        ) = build_test_orchestrator()

    async def run_command(self, command: ChatCommand):
        return await self.orchestrator.handle(command=command)

    async def test_general_advice_returns_text_only_decision(self) -> None:
        self.reasoner.route = "text_only"
        response = await self.run_command(
            ChatCommand(
                session_id="general-1",
                locale="en",
                message="How can I modernize a white shirt?",
                user_message_id=1,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_ONLY)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.COMPLETED)
        self.assertEqual(response.telemetry["provider"], "fake-vllm")

    async def test_garment_matching_start_then_followup_creates_generation_job(self) -> None:
        start_response = await self.run_command(
            ChatCommand(
                session_id="garment-1",
                locale="ru",
                    message="Помоги подобрать образ к вещи",
                    requested_intent=ChatMode.GARMENT_MATCHING,
                    command_name="garment_matching",
                    command_step="start",
                    user_message_id=1,
                    metadata={"clientMessageId": "msg-1"},
            )
        )

        self.assertEqual(start_response.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.flow_state, FlowState.AWAITING_ANCHOR_GARMENT)

        self.reasoner.reply_text = "Собрала образ вокруг рубашки."
        self.reasoner.route = "text_and_generation"
        followup_response = await self.run_command(
            ChatCommand(
                session_id="garment-1",
                locale="ru",
                    message="Темно-синяя джинсовая рубашка прямого кроя",
                    user_message_id=2,
                    metadata={"clientMessageId": "msg-2"},
                    profile_context={"gender": "male"},
            )
        )

        self.assertEqual(followup_response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(followup_response.job_id, "job-1")
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)
        self.assertIsNotNone(self.context_store.context.anchor_garment)
        self.assertTrue(self.context_store.context.anchor_garment.is_sufficient_for_generation)
        self.assertEqual(len(self.scheduler.enqueued), 1)
        self.assertEqual(self.scheduler.enqueued[0].generation_intent.trigger, "garment_matching")
        self.assertEqual(
            self.scheduler.enqueued[0].generation_intent.reason,
            "anchor_garment_is_sufficient_for_generation",
        )
        self.assertTrue(self.event_logger.events)
        self.assertEqual(self.event_logger.events[-1][1]["client_message_id"], "msg-2")

    async def test_style_exploration_uses_history_and_anti_repeat(self) -> None:
        self.reasoner.route = "text_and_generation"
        first_response = await self.run_command(
            ChatCommand(
                    session_id="style-1",
                    locale="en",
                    message="Try another style",
                    requested_intent=ChatMode.STYLE_EXPLORATION,
                    command_name="style_exploration",
                    command_step="start",
                    user_message_id=1,
                    metadata={"clientMessageId": "style-1"},
            )
        )
        second_response = await self.run_command(
            ChatCommand(
                    session_id="style-1",
                    locale="en",
                    message="Try another style",
                    requested_intent=ChatMode.STYLE_EXPLORATION,
                    command_name="style_exploration",
                    command_step="start",
                    user_message_id=2,
                    metadata={"clientMessageId": "style-2"},
            )
        )

        self.assertEqual(first_response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(second_response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertGreaterEqual(len(self.context_store.context.style_history), 2)
        self.assertNotEqual(
            self.context_store.context.style_history[-1].style_id,
            self.context_store.context.style_history[-2].style_id,
        )
        self.assertTrue(second_response.telemetry["style_history_used"])

    async def test_occasion_outfit_clarification_then_generation(self) -> None:
        self.reasoner.occasion_output = OccasionExtractionOutput()
        first_response = await self.run_command(
            ChatCommand(
                session_id="occasion-1",
                locale="ru",
                    message="Мне нужен образ на событие",
                    requested_intent=ChatMode.OCCASION_OUTFIT,
                    command_name="occasion_outfit",
                    command_step="start",
                    user_message_id=1,
                    metadata={"clientMessageId": "occ-1"},
            )
        )

        self.assertEqual(first_response.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.flow_state, FlowState.AWAITING_OCCASION_DETAILS)

        self.reasoner.route = "text_and_generation"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            event_type="wedding",
            dress_code="cocktail",
            time_of_day="evening",
            season_or_weather="spring",
            provider="fake-vllm",
        )
        second_response = await self.run_command(
            ChatCommand(
                session_id="occasion-1",
                locale="ru",
                    message="На свадьбу вечером весной, dress code cocktail",
                    user_message_id=2,
                    metadata={"clientMessageId": "occ-2"},
            )
        )

        self.assertEqual(second_response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)
        self.assertEqual(self.context_store.context.occasion_context.event_type, "wedding")
        self.assertEqual(self.context_store.context.occasion_context.time_of_day, "evening")
        self.assertEqual(self.context_store.context.occasion_context.season, "spring")
        self.assertEqual(self.context_store.context.occasion_context.dress_code, "cocktail")
        self.assertEqual(second_response.telemetry["knowledge_items_count"], 2)

    async def test_provider_error_uses_fallback_and_keeps_telemetry(self) -> None:
        self.reasoner.raise_error = True
        response = await self.run_command(
            ChatCommand(
                session_id="fallback-1",
                locale="en",
                    message="Try another style",
                    requested_intent=ChatMode.STYLE_EXPLORATION,
                    command_name="style_exploration",
                    command_step="start",
                    user_message_id=1,
                    metadata={"clientMessageId": "fallback-1"},
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertTrue(response.telemetry["fallback_used"])
        self.assertEqual(response.telemetry["provider"], "fake-fallback")
        self.assertEqual(response.telemetry["reasoning_mode"], "fallback")

    async def test_context_limit_returns_recoverable_error(self) -> None:
        self.reasoner.raise_context_limit = True
        response = await self.run_command(
            ChatCommand(
                session_id="recoverable-1",
                locale="en",
                    message="How can I modernize this outfit?",
                    user_message_id=1,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.ERROR_RECOVERABLE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.RECOVERABLE_ERROR)
        self.assertEqual(response.telemetry["reasoning_mode"], "context_limit")

    async def test_generation_idempotency_reuses_existing_job_without_second_enqueue(self) -> None:
        self.reasoner.route = "text_and_generation"
        first_response = await self.run_command(
            ChatCommand(
                session_id="idem-1",
                locale="ru",
                    message="Темно-синяя джинсовая рубашка прямого кроя",
                    requested_intent=ChatMode.GARMENT_MATCHING,
                    command_name="garment_matching",
                    command_step="start",
                    user_message_id=1,
                    metadata={"clientMessageId": "idem-1"},
            )
        )
        second_response = await self.run_command(
            ChatCommand(
                session_id="idem-1",
                locale="ru",
                    message="Темно-синяя джинсовая рубашка прямого кроя",
                    requested_intent=ChatMode.GARMENT_MATCHING,
                    command_name="garment_matching",
                    command_step="followup",
                    user_message_id=1,
                    metadata={"clientMessageId": "idem-1"},
            )
        )

        self.assertIsNone(first_response.job_id)
        self.assertEqual(second_response.job_id, "job-1")
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_event_log_contains_command_and_correlation_ids(self) -> None:
        self.reasoner.route = "text_only"
        await self.run_command(
            ChatCommand(
                session_id="ids-1",
                locale="en",
                    message="How can I modernize this shirt?",
                    user_message_id=7,
                    client_message_id="client-7",
                    command_id="cmd-7",
                    correlation_id="corr-7",
            )
        )

        event_name, payload = self.event_logger.events[-1]
        self.assertEqual(event_name, "stylist_chat_orchestrated")
        self.assertEqual(payload["client_message_id"], "client-7")
        self.assertEqual(payload["command_id"], "cmd-7")
        self.assertEqual(payload["correlation_id"], "corr-7")
        self.assertIn("latency_ms", payload)

    async def test_reasoning_uses_conversation_memory_as_primary_source(self) -> None:
        self.context_store.context.remember(role="assistant", content="Memory says use cleaner lines.")
        self.reasoner.route = "text_only"

        await self.run_command(
            ChatCommand(
                session_id="memory-1",
                locale="en",
                    message="What should I add next?",
                    user_message_id=3,
            )
        )

        assert self.reasoner.last_reasoning_input is not None
        history = self.reasoner.last_reasoning_input["conversation_history"]
        self.assertEqual(history[0]["role"], "assistant")
        self.assertIn("cleaner lines", history[0]["content"])

    async def test_garment_matching_start_always_returns_entry_clarification(self) -> None:
        self.reasoner.route = "text_and_generation"
        response = await self.run_command(
            ChatCommand(
                session_id="garment-start-1",
                locale="en",
                    message="Dark indigo denim shirt with a straight fit",
                    requested_intent=ChatMode.GARMENT_MATCHING,
                    command_name="garment_matching",
                    command_step="start",
                    user_message_id=10,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.flow_state, FlowState.AWAITING_ANCHOR_GARMENT)
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_occasion_start_always_returns_entry_clarification(self) -> None:
        self.reasoner.route = "text_and_generation"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            event_type="wedding",
            dress_code="cocktail",
            time_of_day="evening",
            season_or_weather="spring",
        )
        response = await self.run_command(
            ChatCommand(
                session_id="occasion-start-1",
                locale="en",
                    message="Need a spring evening wedding outfit with cocktail dress code",
                    requested_intent=ChatMode.OCCASION_OUTFIT,
                    command_name="occasion_outfit",
                    command_step="start",
                    user_message_id=11,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.flow_state, FlowState.AWAITING_OCCASION_DETAILS)
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_reasoning_context_includes_asset_metadata(self) -> None:
        self.reasoner.route = "text_only"
        asset = SimpleNamespace(
            id=42,
            original_filename="shirt-reference.jpg",
            mime_type="image/jpeg",
            size_bytes=2048,
            asset_type=SimpleNamespace(value="image"),
        )
        await self.run_command(
            ChatCommand(
                session_id="asset-1",
                locale="en",
                message="Suggest a cleaner styling direction",
                user_message_id=12,
                asset_metadata={
                    "asset_id": asset.id,
                    "original_filename": asset.original_filename,
                    "mime_type": asset.mime_type,
                    "size_bytes": asset.size_bytes,
                    "asset_type": asset.asset_type.value,
                },
            )
        )

        assert self.reasoner.last_reasoning_input is not None
        asset_metadata = self.reasoner.last_reasoning_input["asset_metadata"]
        self.assertEqual(asset_metadata["asset_id"], 42)
        self.assertEqual(asset_metadata["original_filename"], "shirt-reference.jpg")
        self.assertEqual(asset_metadata["mime_type"], "image/jpeg")
        self.assertEqual(asset_metadata["size_bytes"], 2048)
        self.assertEqual(asset_metadata["asset_type"], "image")
