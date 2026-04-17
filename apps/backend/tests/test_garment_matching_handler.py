import unittest

from app.application.product_behavior.services.generation_policy_service import GenerationPolicyService
from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import KnowledgeResult, ReasoningOutput
from app.application.stylist_chat.handlers.garment_matching_handler import GarmentMatchingHandler
from app.application.stylist_chat.results.decision_result import DecisionType
from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder
from app.application.stylist_chat.services.garment_brief_compiler import GarmentBriefCompiler
from app.application.stylist_chat.services.garment_clarification_service import GarmentClarificationService
from app.application.stylist_chat.services.garment_matching_context_builder import GarmentMatchingContextBuilder
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.application.stylist_chat.services.reasoning_context_builder import ReasoningContextBuilder
from app.application.stylist_chat.use_cases.build_garment_outfit_brief import BuildGarmentOutfitBriefUseCase
from app.application.stylist_chat.use_cases.continue_garment_matching import ContinueGarmentMatchingUseCase
from app.application.stylist_chat.use_cases.start_garment_matching import StartGarmentMatchingUseCase
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.garment_matching.policies.garment_clarification_policy import GarmentClarificationPolicy
from app.domain.garment_matching.policies.garment_completeness_policy import GarmentCompletenessPolicy
from app.infrastructure.knowledge.garment_knowledge_provider import StaticGarmentKnowledgeProvider
from app.infrastructure.llm.llm_garment_extractor import LLMGarmentExtractorAdapter


class FakeReasoner:
    def __init__(self) -> None:
        self.route = "text_and_generation"
        self.last_input: dict[str, object] | None = None

    async def decide(self, *, locale: str, reasoning_input: dict[str, object]) -> ReasoningOutput:
        self.last_input = reasoning_input
        return ReasoningOutput(
            reply_text="Built a coherent garment-based outfit.",
            image_brief_en="cohesive garment flat lay",
            route=self.route,
            provider="fake-vllm",
        )

    async def extract_occasion_slots(self, **kwargs):
        raise AssertionError("occasion extraction is not used in garment handler tests")


class FakeFallbackReasoner:
    async def decide(self, *, locale: str, reasoning_input: dict[str, object]) -> ReasoningOutput:
        return ReasoningOutput(
            reply_text="Fallback garment reply",
            image_brief_en="fallback garment brief",
            route="text_and_generation",
            provider="fake-fallback",
            reasoning_mode="fallback",
        )


class FakeKnowledgeProvider:
    async def fetch(self, *, query: dict[str, object]) -> KnowledgeResult:
        return KnowledgeResult(items=[], source="unused", query=query)


class FakePromptBuilder:
    async def build(self, *, brief: dict[str, object]) -> dict[str, object]:
        garment_outfit_brief = brief.get("garment_outfit_brief") or {}
        return {
            "prompt": f"prompt::{garment_outfit_brief.get('anchor_summary', 'none')}",
            "image_brief_en": brief.get("image_brief_en", ""),
            "recommendation_text": brief.get("recommendation_text", ""),
            "input_asset_id": brief.get("asset_id"),
            "metadata": {"workflow_name": "garment_matching_variation"},
        }


class GarmentMatchingHandlerLogicTests(unittest.IsolatedAsyncioTestCase):
    def build_handler(self) -> tuple[GarmentMatchingHandler, FakeReasoner]:
        reasoner = FakeReasoner()
        clarification_builder = ClarificationMessageBuilder()
        garment_brief_compiler = GarmentBriefCompiler()
        handler = GarmentMatchingHandler(
            start_use_case=StartGarmentMatchingUseCase(clarification_builder),
            continue_use_case=ContinueGarmentMatchingUseCase(
                garment_extractor=LLMGarmentExtractorAdapter(),
                garment_completeness_evaluator=GarmentCompletenessPolicy(),
                garment_clarification_service=GarmentClarificationService(GarmentClarificationPolicy()),
            ),
            build_outfit_brief_use_case=BuildGarmentOutfitBriefUseCase(
                garment_knowledge_provider=StaticGarmentKnowledgeProvider(),
                garment_matching_context_builder=GarmentMatchingContextBuilder(),
                outfit_brief_builder=garment_brief_compiler,
                garment_brief_compiler=garment_brief_compiler,
            ),
            reasoner=reasoner,
            fallback_reasoner=FakeFallbackReasoner(),
            knowledge_provider=FakeKnowledgeProvider(),
            reasoning_context_builder=ReasoningContextBuilder(),
            generation_request_builder=GenerationRequestBuilder(
                prompt_builder=FakePromptBuilder(),
                generation_policy_service=GenerationPolicyService(),
            ),
        )
        return handler, reasoner

    async def test_start_command_returns_entry_clarification(self) -> None:
        handler, _ = self.build_handler()
        context = ChatModeContext(active_mode=ChatMode.GARMENT_MATCHING)

        decision = await handler.handle(
            command=ChatCommand(
                session_id="garment-handler-start",
                locale="en",
                message="Style around a garment",
                command_name="garment_matching",
                command_step="start",
            ),
            context=context,
        )

        self.assertEqual(decision.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(context.flow_state, FlowState.AWAITING_ANCHOR_GARMENT)

    async def test_incomplete_followup_returns_short_clarification(self) -> None:
        handler, _ = self.build_handler()
        context = ChatModeContext(active_mode=ChatMode.GARMENT_MATCHING)
        context.flow_state = FlowState.AWAITING_ANCHOR_GARMENT

        decision = await handler.handle(
            command=ChatCommand(
                session_id="garment-handler-clarify",
                locale="en",
                message="shirt",
            ),
            context=context,
        )

        self.assertEqual(decision.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(context.flow_state, FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION)
        self.assertEqual(decision.telemetry["knowledge_provider_used"], "clarification_policy")

    async def test_sufficient_followup_returns_text_only_with_cta(self) -> None:
        handler, reasoner = self.build_handler()
        context = ChatModeContext(active_mode=ChatMode.GARMENT_MATCHING)
        context.flow_state = FlowState.AWAITING_ANCHOR_GARMENT

        decision = await handler.handle(
            command=ChatCommand(
                session_id="garment-handler-cta",
                locale="en",
                message="black leather jacket",
                command_id="garment-handler-cta",
            ),
            context=context,
        )

        self.assertEqual(decision.decision_type, DecisionType.TEXT_ONLY)
        self.assertTrue(decision.can_offer_visualization)
        self.assertEqual(decision.cta_text, "Build a flat lay around this garment?")
        self.assertTrue(context.anchor_garment.is_sufficient_for_generation)
        self.assertEqual(context.flow_state, FlowState.READY_FOR_GENERATION)
        assert reasoner.last_input is not None
        self.assertIn("garment_outfit_brief", reasoner.last_input)
        self.assertEqual(reasoner.last_input["garment_outfit_brief"]["brief_type"], "garment_matching")

    async def test_cta_confirmation_reuses_anchor_and_generates(self) -> None:
        handler, _ = self.build_handler()
        context = ChatModeContext(active_mode=ChatMode.GARMENT_MATCHING)
        context.flow_state = FlowState.AWAITING_ANCHOR_GARMENT

        await handler.handle(
            command=ChatCommand(
                session_id="garment-handler-confirm",
                locale="en",
                message="black leather jacket",
                command_id="garment-handler-confirm-1",
            ),
            context=context,
        )

        decision = await handler.handle(
            command=ChatCommand(
                session_id="garment-handler-confirm",
                locale="en",
                message="Confirm the visualization",
                command_id="garment-handler-confirm-2",
                metadata={"source": "visualization_cta", "visualization_type": "flat_lay_reference"},
            ),
            context=context,
        )

        self.assertEqual(decision.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertFalse(decision.can_offer_visualization)
        self.assertIsNotNone(decision.generation_payload)

    async def test_explicit_visual_request_reuses_anchor_and_generates(self) -> None:
        handler, _ = self.build_handler()
        context = ChatModeContext(active_mode=ChatMode.GARMENT_MATCHING)
        context.flow_state = FlowState.AWAITING_ANCHOR_GARMENT

        await handler.handle(
            command=ChatCommand(
                session_id="garment-handler-explicit",
                locale="en",
                message="black leather jacket",
                command_id="garment-handler-explicit-1",
            ),
            context=context,
        )

        decision = await handler.handle(
            command=ChatCommand(
                session_id="garment-handler-explicit",
                locale="en",
                message="Visualize it as a flat lay",
                command_id="garment-handler-explicit-2",
                metadata={"source": "explicit_visual_request"},
            ),
            context=context,
        )

        self.assertEqual(decision.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertIsNotNone(decision.generation_payload)
