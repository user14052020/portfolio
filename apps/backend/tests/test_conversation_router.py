import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import RouterClientOutput, RouterClientTransportError
from app.application.stylist_chat.services.conversation_router import ConversationRouter
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.routing import RouterFailureReason, RoutingMode


class FakeRouterClient:
    def __init__(self, *, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = payload or {}
        self.error = error
        self.calls = 0

    async def route(self, *, routing_input):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return RouterClientOutput(
            payload=self.payload,
            provider="fake-vllm-router",
            raw_content='{"mode":"occasion_outfit"}',
        )


class ConversationRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_route_returns_validated_router_decision(self) -> None:
        router = ConversationRouter(
            router_client=FakeRouterClient(
                payload={
                    "mode": "occasion_outfit",
                    "confidence": 0.86,
                    "needs_clarification": False,
                    "missing_slots": [],
                    "generation_intent": False,
                    "continue_existing_flow": False,
                    "should_reset_to_general": False,
                    "reasoning_depth": "normal",
                    "retrieval_profile": "occasion_focused",
                }
            )
        )

        result = await router.route(
            command=ChatCommand(
                session_id="router-valid-1",
                locale="en",
                message="I need a look for a gallery opening",
            ),
            context=ChatModeContext(),
        )

        self.assertEqual(result.decision.mode, RoutingMode.OCCASION_OUTFIT)
        self.assertEqual(result.decision.retrieval_profile, "occasion_focused")
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.provider, "fake-vllm-router")
        self.assertEqual(result.validation_errors, [])

    async def test_route_falls_back_on_transport_error(self) -> None:
        router = ConversationRouter(
            router_client=FakeRouterClient(
                error=RouterClientTransportError("vLLM router request timed out")
            )
        )

        result = await router.route(
            command=ChatCommand(
                session_id="router-fallback-1",
                locale="en",
                message="hi",
            ),
            context=ChatModeContext(),
        )

        self.assertTrue(result.used_fallback)
        self.assertEqual(result.failure_reason, RouterFailureReason.TIMEOUT)
        self.assertEqual(result.fallback_rule, "obvious_greeting")
        self.assertEqual(result.decision.mode, RoutingMode.GENERAL_ADVICE)

    async def test_explicit_style_button_bypasses_router_even_during_clarification_flow(self) -> None:
        router_client = FakeRouterClient(
            payload={
                "mode": "clarification_only",
                "confidence": 0.92,
                "needs_clarification": True,
                "missing_slots": ["occasion_details"],
                "generation_intent": False,
                "continue_existing_flow": True,
                "should_reset_to_general": False,
                "reasoning_depth": "light",
            }
        )
        router = ConversationRouter(router_client=router_client)

        result = await router.route(
            command=ChatCommand(
                session_id="router-style-button-1",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                metadata={"source": "quick_action"},
            ),
            context=ChatModeContext(
                active_mode=ChatMode.OCCASION_OUTFIT,
                flow_state=FlowState.AWAITING_OCCASION_CLARIFICATION,
                pending_clarification="Tell me about the event",
            ),
        )

        self.assertEqual(router_client.calls, 0)
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.provider, "fallback_router_policy")
        self.assertEqual(result.fallback_rule, "explicit_style_button")
        self.assertEqual(result.decision.mode, RoutingMode.STYLE_EXPLORATION)
        self.assertTrue(result.decision.generation_intent)

    async def test_new_general_question_bypasses_router_during_clarification_flow(self) -> None:
        router_client = FakeRouterClient(
            payload={
                "mode": "clarification_only",
                "confidence": 0.92,
                "needs_clarification": True,
                "missing_slots": ["occasion_details"],
                "generation_intent": False,
                "continue_existing_flow": True,
                "should_reset_to_general": False,
                "reasoning_depth": "light",
            }
        )
        router = ConversationRouter(router_client=router_client)

        result = await router.route(
            command=ChatCommand(
                session_id="router-general-pivot-1",
                locale="ru",
                message="\u0447\u0442\u043e \u0442\u044b \u0437\u043d\u0430\u0435\u0448\u044c \u043e \u0436\u0435\u043b\u0442\u043e\u043c \u0446\u0432\u0435\u0442\u0435",
            ),
            context=ChatModeContext(
                active_mode=ChatMode.OCCASION_OUTFIT,
                flow_state=FlowState.AWAITING_OCCASION_CLARIFICATION,
                pending_clarification="Tell me about the event",
            ),
        )

        self.assertEqual(router_client.calls, 0)
        self.assertTrue(result.used_fallback)
        self.assertEqual(result.provider, "fallback_router_policy")
        self.assertEqual(result.fallback_rule, "clarification_flow_general_pivot")
        self.assertEqual(result.decision.mode, RoutingMode.GENERAL_ADVICE)
        self.assertFalse(result.decision.needs_clarification)
