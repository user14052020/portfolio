import json
import unittest

from app.application.product_behavior.services.conversation_state_policy import ConversationStatePolicy
from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import OccasionExtractionOutput, RouterClientOutput
from app.application.stylist_chat.orchestrator.command_dispatcher import CommandDispatcher
from app.application.stylist_chat.results.decision_result import DecisionType
from app.application.stylist_chat.services.conversation_router import ConversationRouter
from app.domain.chat_modes import ChatMode
from app.models.enums import GenerationStatus

try:
    from test_stylist_orchestrator import build_test_orchestrator
except ModuleNotFoundError:
    from tests.test_stylist_orchestrator import build_test_orchestrator


HELLO_RU = "\u043f\u0440\u0438\u0432\u0435\u0442"
EXHIBITION_QUERY_RU = (
    "\u0447\u0442\u043e \u043d\u0430\u0434\u0435\u0442\u044c "
    "\u043d\u0430 \u0432\u044b\u0441\u0442\u0430\u0432\u043a\u0443 \u0432\u0435\u0447\u0435\u0440\u043e\u043c?"
)
FLAT_LAY_QUERY_RU = "\u0441\u043e\u0431\u0435\u0440\u0438 flat lay"


class FakeSemanticRouterClient:
    async def route(self, *, routing_input) -> RouterClientOutput:
        text = routing_input.user_message.strip().lower()
        active_mode = routing_input.active_mode.value if routing_input.active_mode is not None else None

        if routing_input.last_ui_action == "try_other_style" or "try another style" in text:
            payload = self._payload(
                mode="style_exploration",
                confidence=0.96,
                generation_intent=True,
            )
        elif text == HELLO_RU:
            payload = self._payload(
                mode="general_advice",
                confidence=0.93,
                should_reset_to_general=active_mode not in {None, "general_advice"},
                reasoning_depth="light",
            )
        elif "\u0432\u044b\u0441\u0442\u0430\u0432" in text and "\u0432\u0435\u0447\u0435\u0440" in text:
            payload = self._payload(
                mode="occasion_outfit",
                confidence=0.89,
                reasoning_depth="normal",
            )
        elif "flat lay" in text or "flatlay" in text:
            payload = self._payload(
                mode=active_mode or "general_advice",
                confidence=0.84,
                generation_intent=True,
                reasoning_depth="normal",
            )
        else:
            payload = self._payload(
                mode="general_advice",
                confidence=0.81,
                should_reset_to_general=active_mode not in {None, "general_advice"},
                reasoning_depth="light",
            )

        return RouterClientOutput(
            payload=payload,
            provider="fake-semantic-router",
            raw_content=json.dumps(payload, ensure_ascii=True),
        )

    def _payload(
        self,
        *,
        mode: str,
        confidence: float,
        generation_intent: bool = False,
        continue_existing_flow: bool = False,
        should_reset_to_general: bool = False,
        reasoning_depth: str = "normal",
    ) -> dict[str, object]:
        return {
            "mode": mode,
            "confidence": confidence,
            "needs_clarification": False,
            "missing_slots": [],
            "generation_intent": generation_intent,
            "continue_existing_flow": continue_existing_flow,
            "should_reset_to_general": should_reset_to_general,
            "reasoning_depth": reasoning_depth,
        }


class RoutingProductScenarioTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        (
            self.orchestrator,
            self.context_store,
            self.reasoner,
            self.scheduler,
            self.event_logger,
            _metrics_recorder,
            _checkpoint_writer,
        ) = build_test_orchestrator()
        self.orchestrator.command_dispatcher = CommandDispatcher(
            conversation_router=ConversationRouter(router_client=FakeSemanticRouterClient()),
            conversation_state_policy=ConversationStatePolicy(),
        )

    async def run_command(self, command: ChatCommand):
        return await self.orchestrator.handle(command=command)

    def latest_event_payload(self, event_name: str) -> dict[str, object]:
        events = [payload for name, payload in self.event_logger.events if name == event_name]
        self.assertTrue(events)
        return events[-1]

    async def test_privet_routes_to_general_advice(self) -> None:
        self.reasoner.route = "text_only"

        response = await self.run_command(
            ChatCommand(
                session_id="routing-product-hello-1",
                locale="ru",
                message=HELLO_RU,
                user_message_id=1,
            )
        )

        routed = self.latest_event_payload("stylist_chat_routed")
        self.assertEqual(routed["routing_mode"], "general_advice")
        self.assertEqual(response.decision_type, DecisionType.TEXT_ONLY)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_exhibition_evening_query_routes_to_occasion_outfit(self) -> None:
        self.reasoner.route = "text_only"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            event_type="exhibition",
            time_of_day="evening",
        )

        response = await self.run_command(
            ChatCommand(
                session_id="routing-product-exhibition-1",
                locale="ru",
                message=EXHIBITION_QUERY_RU,
                user_message_id=1,
            )
        )

        routed = self.latest_event_payload("stylist_chat_routed")
        self.assertEqual(routed["routing_mode"], "occasion_outfit")
        self.assertEqual(self.context_store.context.active_mode, ChatMode.OCCASION_OUTFIT)
        self.assertEqual(response.decision_type, DecisionType.CLARIFICATION_REQUIRED)

    async def test_soberi_flat_lay_sets_generation_intent_true(self) -> None:
        self.reasoner.route = "text_and_generation"

        response = await self.run_command(
            ChatCommand(
                session_id="routing-product-flatlay-1",
                locale="ru",
                message=FLAT_LAY_QUERY_RU,
                user_message_id=1,
            )
        )

        routed = self.latest_event_payload("stylist_chat_routed")
        self.assertEqual(routed["generation_intent"], True)
        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(response.job_id, "job-1")
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_after_style_exploration_free_text_returns_to_general_advice(self) -> None:
        self.reasoner.route = "text_and_generation"
        first = await self.run_command(
            ChatCommand(
                session_id="routing-product-reset-1",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
                metadata={"source": "quick_action"},
            )
        )

        self.assertEqual(first.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.STYLE_EXPLORATION)

        self.scheduler.job_statuses["job-1"] = GenerationStatus.COMPLETED
        self.reasoner.route = "text_only"

        followup = await self.run_command(
            ChatCommand(
                session_id="routing-product-reset-1",
                locale="en",
                message="What shoes would work for everyday wear?",
                user_message_id=2,
            )
        )

        routed = self.latest_event_payload("stylist_chat_routed")
        self.assertEqual(routed["routing_mode"], "general_advice")
        self.assertEqual(followup.decision_type, DecisionType.TEXT_ONLY)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(len(self.scheduler.enqueued), 1)
