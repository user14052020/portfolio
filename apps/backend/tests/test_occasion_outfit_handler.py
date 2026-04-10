import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import (
    GenerationScheduleRequest,
    GenerationScheduleResult,
    KnowledgeItem,
    KnowledgeResult,
    OccasionExtractionOutput,
    ReasoningOutput,
)
from app.application.stylist_chat.handlers.occasion_outfit_handler import OccasionOutfitHandler
from app.application.stylist_chat.results.decision_result import DecisionType
from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.application.stylist_chat.services.occasion_brief_compiler import OccasionBriefCompiler
from app.application.stylist_chat.services.occasion_clarification_service import OccasionClarificationService
from app.application.stylist_chat.services.occasion_context_builder import OccasionContextBuilder
from app.application.stylist_chat.services.occasion_extraction_service import OccasionExtractionService
from app.application.stylist_chat.services.reasoning_context_builder import ReasoningContextBuilder
from app.application.stylist_chat.use_cases.build_occasion_outfit_brief import BuildOccasionOutfitBriefUseCase
from app.application.stylist_chat.use_cases.continue_occasion_outfit import ContinueOccasionOutfitUseCase
from app.application.stylist_chat.use_cases.start_occasion_outfit import StartOccasionOutfitUseCase
from app.application.stylist_chat.use_cases.update_occasion_context import UpdateOccasionContextUseCase
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.occasion_outfit.policies.occasion_clarification_policy import OccasionClarificationPolicy
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessPolicy
from app.infrastructure.knowledge.occasion_knowledge_provider import StaticOccasionKnowledgeProvider
from app.models.enums import GenerationStatus


class FakeOccasionReasoner:
    def __init__(self) -> None:
        self.route = "text_and_generation"
        self.reply_text = "Built the occasion outfit."
        self.image_brief = "occasion editorial flat lay"
        self.extraction = OccasionExtractionOutput()

    async def decide(self, *, locale: str, reasoning_input: dict[str, object]) -> ReasoningOutput:
        return ReasoningOutput(
            reply_text=self.reply_text,
            image_brief_en=self.image_brief,
            route=self.route,
            provider="fake-occasion-reasoner",
        )

    async def extract_occasion_slots(
        self,
        *,
        locale: str,
        user_message: str,
        conversation_history: list[dict[str, str]],
        existing_slots: dict[str, str | None],
    ) -> OccasionExtractionOutput:
        return self.extraction


class FakeFallbackReasoner:
    async def decide(self, *, locale: str, reasoning_input: dict[str, object]) -> ReasoningOutput:
        return ReasoningOutput(
            reply_text="Fallback occasion reply",
            image_brief_en="fallback occasion outfit",
            route="text_and_generation",
            provider="fake-fallback",
        )


class FakeKnowledgeProvider:
    async def fetch(self, *, query: dict[str, object]) -> KnowledgeResult:
        return KnowledgeResult(items=[KnowledgeItem("general", "Keep the look coherent.")], source="test", query=query)


class FakePromptBuilder:
    async def build(self, *, brief: dict[str, object]) -> dict[str, object]:
        return {
            "prompt": f"prompt::{brief.get('image_brief_en', '')}",
            "image_brief_en": brief.get("image_brief_en", ""),
            "recommendation_text": brief.get("recommendation_text", ""),
            "input_asset_id": brief.get("asset_id"),
        }


class FakeGenerationScheduler:
    def __init__(self) -> None:
        self.enqueued: list[GenerationScheduleRequest] = []

    async def enqueue(self, request: GenerationScheduleRequest) -> GenerationScheduleResult:
        self.enqueued.append(request)
        return GenerationScheduleResult(
            job_id="occasion-job-1",
            status=GenerationStatus.PENDING.value,
        )

    async def sync_context(self, context: ChatModeContext) -> ChatModeContext:
        return context


def build_handler(reasoner: FakeOccasionReasoner, scheduler: FakeGenerationScheduler) -> OccasionOutfitHandler:
    extraction_service = OccasionExtractionService(reasoner=reasoner)
    continue_use_case = ContinueOccasionOutfitUseCase(
        occasion_context_extractor=extraction_service,
        update_occasion_context=UpdateOccasionContextUseCase(
            completeness_evaluator=OccasionCompletenessPolicy()
        ),
        occasion_clarification_service=OccasionClarificationService(OccasionClarificationPolicy()),
    )
    build_outfit_brief = BuildOccasionOutfitBriefUseCase(
        occasion_knowledge_provider=StaticOccasionKnowledgeProvider(),
        occasion_context_builder=OccasionContextBuilder(),
        outfit_brief_builder=OccasionBriefCompiler(),
        occasion_brief_compiler=OccasionBriefCompiler(),
    )
    return OccasionOutfitHandler(
        start_use_case=StartOccasionOutfitUseCase(ClarificationMessageBuilder()),
        continue_use_case=continue_use_case,
        build_outfit_brief_use_case=build_outfit_brief,
        generation_scheduler=scheduler,
        reasoner=reasoner,
        fallback_reasoner=FakeFallbackReasoner(),
        knowledge_provider=FakeKnowledgeProvider(),
        reasoning_context_builder=ReasoningContextBuilder(),
        generation_request_builder=GenerationRequestBuilder(prompt_builder=FakePromptBuilder()),
    )


class OccasionOutfitHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_command_enters_occasion_flow(self) -> None:
        reasoner = FakeOccasionReasoner()
        scheduler = FakeGenerationScheduler()
        handler = build_handler(reasoner, scheduler)
        context = ChatModeContext()

        response = await handler.handle(
            command=ChatCommand(
                session_id="occasion-handler-1",
                locale="en",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                message="Need an event outfit",
                user_message_id=1,
            ),
            context=context,
        )

        self.assertEqual(response.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(context.flow_state, FlowState.AWAITING_OCCASION_DETAILS)

    async def test_followup_with_missing_slots_returns_slot_specific_clarification(self) -> None:
        reasoner = FakeOccasionReasoner()
        scheduler = FakeGenerationScheduler()
        handler = build_handler(reasoner, scheduler)
        context = ChatModeContext(active_mode=ChatMode.OCCASION_OUTFIT)
        StartOccasionOutfitUseCase(ClarificationMessageBuilder()).execute(context=context, locale="en")
        reasoner.extraction = OccasionExtractionOutput(event_type="exhibition")

        response = await handler.handle(
            command=ChatCommand(
                session_id="occasion-handler-2",
                locale="en",
                message="It is for an exhibition",
                user_message_id=2,
            ),
            context=context,
        )

        self.assertEqual(response.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(context.flow_state, FlowState.AWAITING_OCCASION_CLARIFICATION)
        self.assertIn("time of day", (response.text_reply or "").lower())
        self.assertEqual(len(scheduler.enqueued), 0)

    async def test_followup_with_sufficient_slots_generates_job(self) -> None:
        reasoner = FakeOccasionReasoner()
        scheduler = FakeGenerationScheduler()
        handler = build_handler(reasoner, scheduler)
        context = ChatModeContext(active_mode=ChatMode.OCCASION_OUTFIT)
        StartOccasionOutfitUseCase(ClarificationMessageBuilder()).execute(context=context, locale="en")
        reasoner.extraction = OccasionExtractionOutput(
            event_type="wedding",
            time_of_day="day",
            season_or_weather="summer",
            desired_impression="elegant",
        )

        response = await handler.handle(
            command=ChatCommand(
                session_id="occasion-handler-3",
                locale="en",
                message="Day wedding in summer, I want to look elegant",
                user_message_id=3,
                command_id="occasion-handler-3",
            ),
            context=context,
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(response.job_id, "occasion-job-1")
        self.assertEqual(context.flow_state, FlowState.GENERATION_QUEUED)
        self.assertEqual(context.occasion_context.event_type, "wedding")
        self.assertEqual(context.occasion_context.time_of_day, "day")
        self.assertEqual(context.occasion_context.season, "summer")
        self.assertEqual(context.occasion_context.desired_impression, "elegant")
        self.assertEqual(len(scheduler.enqueued), 1)
