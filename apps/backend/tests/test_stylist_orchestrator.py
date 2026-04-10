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
from app.application.stylist_chat.services.garment_brief_compiler import GarmentBriefCompiler
from app.application.stylist_chat.services.garment_clarification_service import GarmentClarificationService
from app.application.stylist_chat.services.garment_matching_context_builder import GarmentMatchingContextBuilder
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.application.stylist_chat.services.occasion_brief_compiler import OccasionBriefCompiler
from app.application.stylist_chat.services.occasion_clarification_service import OccasionClarificationService
from app.application.stylist_chat.services.occasion_context_builder import OccasionContextBuilder
from app.application.stylist_chat.services.occasion_extraction_service import OccasionExtractionService
from app.application.stylist_chat.services.reasoning_context_builder import ReasoningContextBuilder
from app.application.stylist_chat.use_cases.build_garment_outfit_brief import BuildGarmentOutfitBriefUseCase
from app.application.stylist_chat.use_cases.build_occasion_outfit_brief import BuildOccasionOutfitBriefUseCase
from app.application.stylist_chat.use_cases.continue_garment_matching import ContinueGarmentMatchingUseCase
from app.application.stylist_chat.use_cases.continue_occasion_outfit import ContinueOccasionOutfitUseCase
from app.application.stylist_chat.use_cases.start_garment_matching import StartGarmentMatchingUseCase
from app.application.stylist_chat.use_cases.start_occasion_outfit import StartOccasionOutfitUseCase
from app.application.stylist_chat.use_cases.update_occasion_context import UpdateOccasionContextUseCase
from app.domain.chat_context import ChatModeContext, StyleDirectionContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.garment_matching.policies.garment_clarification_policy import GarmentClarificationPolicy
from app.domain.garment_matching.policies.garment_completeness_policy import GarmentCompletenessPolicy
from app.domain.occasion_outfit.policies.occasion_clarification_policy import OccasionClarificationPolicy
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessPolicy
from app.infrastructure.knowledge.occasion_knowledge_provider import StaticOccasionKnowledgeProvider
from app.infrastructure.knowledge.garment_knowledge_provider import StaticGarmentKnowledgeProvider
from app.infrastructure.llm.llm_garment_extractor import LLMGarmentExtractorAdapter
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
        self.fail_next = False

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
        if self.fail_next:
            self.fail_next = False
            return GenerationScheduleResult(
                job_id=None,
                status=GenerationStatus.FAILED.value,
                job=None,
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
    garment_matching_context_builder = GarmentMatchingContextBuilder()
    garment_brief_compiler = GarmentBriefCompiler()
    occasion_context_builder = OccasionContextBuilder()
    occasion_brief_compiler = OccasionBriefCompiler()
    garment_extractor = LLMGarmentExtractorAdapter()
    occasion_extractor = OccasionExtractionService(reasoner=reasoner)
    garment_completeness_policy = GarmentCompletenessPolicy()
    garment_clarification_policy = GarmentClarificationPolicy()
    garment_clarification_service = GarmentClarificationService(garment_clarification_policy)
    occasion_completeness_policy = OccasionCompletenessPolicy()
    occasion_clarification_policy = OccasionClarificationPolicy()
    occasion_clarification_service = OccasionClarificationService(occasion_clarification_policy)
    garment_knowledge_provider = StaticGarmentKnowledgeProvider()
    occasion_knowledge_provider = StaticOccasionKnowledgeProvider()
    start_garment_matching = StartGarmentMatchingUseCase(clarification_builder)
    start_occasion_outfit = StartOccasionOutfitUseCase(clarification_builder)
    continue_garment_matching = ContinueGarmentMatchingUseCase(
        garment_extractor=garment_extractor,
        garment_completeness_evaluator=garment_completeness_policy,
        garment_clarification_service=garment_clarification_service,
    )
    continue_occasion_outfit = ContinueOccasionOutfitUseCase(
        occasion_context_extractor=occasion_extractor,
        update_occasion_context=UpdateOccasionContextUseCase(
            completeness_evaluator=occasion_completeness_policy,
        ),
        occasion_clarification_service=occasion_clarification_service,
    )
    build_garment_outfit_brief = BuildGarmentOutfitBriefUseCase(
        garment_knowledge_provider=garment_knowledge_provider,
        garment_matching_context_builder=garment_matching_context_builder,
        outfit_brief_builder=garment_brief_compiler,
        garment_brief_compiler=garment_brief_compiler,
    )
    build_occasion_outfit_brief = BuildOccasionOutfitBriefUseCase(
        occasion_knowledge_provider=occasion_knowledge_provider,
        occasion_context_builder=occasion_context_builder,
        outfit_brief_builder=occasion_brief_compiler,
        occasion_brief_compiler=occasion_brief_compiler,
    )
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
            start_use_case=start_garment_matching,
            continue_use_case=continue_garment_matching,
            build_outfit_brief_use_case=build_garment_outfit_brief,
            generation_scheduler=generation_scheduler,
            **shared_kwargs,
        ),
        ChatMode.OCCASION_OUTFIT: OccasionOutfitHandler(
            start_use_case=start_occasion_outfit,
            continue_use_case=continue_occasion_outfit,
            build_outfit_brief_use_case=build_occasion_outfit_brief,
            generation_scheduler=generation_scheduler,
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
        self.assertEqual(self.event_logger.events[-1][1]["knowledge_provider_used"], "garment_static_knowledge")
        self.assertGreater(self.event_logger.events[-1][1]["anchor_garment_completeness"], 0.0)

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
        self.assertEqual(second_response.telemetry["knowledge_items_count"], 3)
        self.assertGreater(second_response.telemetry["occasion_completeness"], 0.8)
        self.assertEqual(self.event_logger.events[-1][1]["knowledge_provider_used"], "occasion_static_knowledge")
        self.assertIn("event_type", self.event_logger.events[-1][1]["filled_slots"])

    async def test_occasion_outfit_insufficient_followup_returns_slot_specific_clarification(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="occasion-clarify-1",
                locale="en",
                message="Need an outfit for an event",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
            )
        )
        self.reasoner.occasion_output = OccasionExtractionOutput(event_type="exhibition")

        response = await self.run_command(
            ChatCommand(
                session_id="occasion-clarify-1",
                locale="en",
                message="It is for an exhibition",
                user_message_id=2,
                client_message_id="occasion-clarify-1-followup",
            )
        )

        self.assertEqual(response.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.flow_state, FlowState.AWAITING_OCCASION_CLARIFICATION)
        self.assertIn("time of day", (response.text_reply or "").lower())
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_duplicate_occasion_followup_only_enqueues_one_generation_job(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="occasion-dedupe-1",
                locale="en",
                message="Need an outfit for an event",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
            )
        )
        self.reasoner.route = "text_and_generation"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            event_type="wedding",
            time_of_day="day",
            season_or_weather="summer",
            desired_impression="elegant",
        )

        first = await self.run_command(
            ChatCommand(
                session_id="occasion-dedupe-1",
                locale="en",
                message="Day wedding in summer, I want to look elegant",
                user_message_id=2,
                client_message_id="occasion-dup-1",
                command_id="occasion-dup-1",
            )
        )
        second = await self.run_command(
            ChatCommand(
                session_id="occasion-dedupe-1",
                locale="en",
                message="Day wedding in summer, I want to look elegant",
                user_message_id=2,
                client_message_id="occasion-dup-1",
                command_id="occasion-dup-1",
            )
        )

        self.assertEqual(first.job_id, "job-1")
        self.assertEqual(second.job_id, "job-1")
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_occasion_generation_queue_failure_returns_recoverable_response(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="occasion-queue-failure-1",
                locale="en",
                message="Need an outfit for an event",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
            )
        )
        self.scheduler.fail_next = True
        self.reasoner.route = "text_and_generation"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            event_type="conference",
            time_of_day="day",
            season_or_weather="autumn",
            dress_code="smart casual",
        )

        response = await self.run_command(
            ChatCommand(
                session_id="occasion-queue-failure-1",
                locale="en",
                message="Conference during the day in autumn, smart casual",
                user_message_id=2,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.ERROR_RECOVERABLE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.RECOVERABLE_ERROR)
        self.assertEqual(response.error_code, "generation_enqueue_failed")

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

    async def test_garment_matching_incomplete_description_returns_one_short_clarification(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="garment-clarify-1",
                locale="ru",
                message="Подобрать к вещи",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
            )
        )

        response = await self.run_command(
            ChatCommand(
                session_id="garment-clarify-1",
                locale="ru",
                message="рубашка",
                user_message_id=2,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(
            self.context_store.context.flow_state,
            FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION,
        )
        self.assertLessEqual(len((response.text_reply or "").split("?")), 2)
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_garment_matching_clarification_then_generation(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="garment-clarify-2",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
            )
        )
        first_followup = await self.run_command(
            ChatCommand(
                session_id="garment-clarify-2",
                locale="en",
                message="shirt",
                user_message_id=2,
            )
        )
        self.assertEqual(first_followup.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.reasoner.route = "text_and_generation"
        second_followup = await self.run_command(
            ChatCommand(
                session_id="garment-clarify-2",
                locale="en",
                message="white linen",
                user_message_id=3,
                command_id="garment-clarify-2-followup",
            )
        )

        self.assertEqual(second_followup.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(second_followup.job_id, "job-1")
        assert self.context_store.context.anchor_garment is not None
        self.assertEqual(self.context_store.context.anchor_garment.garment_type, "shirt")
        self.assertEqual(self.context_store.context.anchor_garment.material, "linen")
        self.assertTrue(self.context_store.context.anchor_garment.is_sufficient_for_generation)

    async def test_asset_only_followup_stays_in_garment_flow_then_generates_after_clarification(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="garment-asset-1",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
            )
        )
        first_followup = await self.run_command(
            ChatCommand(
                session_id="garment-asset-1",
                locale="en",
                message="",
                asset_id="asset-1",
                user_message_id=2,
            )
        )
        self.assertEqual(first_followup.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GARMENT_MATCHING)
        self.reasoner.route = "text_and_generation"
        second_followup = await self.run_command(
            ChatCommand(
                session_id="garment-asset-1",
                locale="en",
                message="black leather jacket",
                asset_id="asset-1",
                user_message_id=3,
            )
        )

        self.assertEqual(second_followup.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(second_followup.job_id, "job-1")

    async def test_text_and_asset_followup_path_generates_with_same_job_flow(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="garment-text-asset-1",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
            )
        )
        self.reasoner.route = "text_and_generation"
        response = await self.run_command(
            ChatCommand(
                session_id="garment-text-asset-1",
                locale="en",
                message="white linen shirt",
                asset_id="asset-88",
                user_message_id=2,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(response.job_id, "job-1")
        assert self.context_store.context.anchor_garment is not None
        self.assertEqual(self.context_store.context.anchor_garment.material, "linen")
        self.assertEqual(self.context_store.context.anchor_garment.asset_id, "asset-88")

    async def test_duplicate_followup_only_enqueues_one_generation_job(self) -> None:
        self.reasoner.route = "text_and_generation"
        await self.run_command(
            ChatCommand(
                session_id="garment-dedupe-1",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
            )
        )
        first = await self.run_command(
            ChatCommand(
                session_id="garment-dedupe-1",
                locale="en",
                message="black leather jacket",
                user_message_id=2,
                client_message_id="dup-1",
                command_id="dup-1",
            )
        )
        second = await self.run_command(
            ChatCommand(
                session_id="garment-dedupe-1",
                locale="en",
                message="black leather jacket",
                user_message_id=2,
                client_message_id="dup-1",
                command_id="dup-1",
            )
        )

        self.assertEqual(first.job_id, "job-1")
        self.assertEqual(second.job_id, "job-1")
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_generation_queue_failure_returns_graceful_recoverable_response(self) -> None:
        self.reasoner.route = "text_and_generation"
        self.scheduler.fail_next = True
        await self.run_command(
            ChatCommand(
                session_id="garment-queue-failure-1",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
            )
        )
        response = await self.run_command(
            ChatCommand(
                session_id="garment-queue-failure-1",
                locale="en",
                message="black leather jacket",
                user_message_id=2,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.ERROR_RECOVERABLE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.RECOVERABLE_ERROR)
        self.assertEqual(response.error_code, "generation_enqueue_failed")

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
        self.assertEqual(payload["active_mode"], "general_advice")
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
