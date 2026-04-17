import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import RouterClientOutput, RouterClientTransportError
from app.application.stylist_chat.services.conversation_router import ConversationRouter
from app.domain.chat_context import ChatModeContext
from app.domain.routing import RouterFailureReason, RoutingMode


class FakeRouterClient:
    def __init__(self, *, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = payload or {}
        self.error = error

    async def route(self, *, routing_input):
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
