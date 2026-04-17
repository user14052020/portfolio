import unittest

from app.application.product_behavior.services.conversation_state_policy import ConversationStatePolicy
from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import RouterClientOutput
from app.application.stylist_chat.orchestrator.command_dispatcher import CommandDispatcher
from app.application.stylist_chat.services.conversation_router import ConversationRouter
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.routing import RouterFailureReason, RoutingMode


class FakeRouterClient:
    def __init__(self, *, payload) -> None:
        self.payload = payload

    async def route(self, *, routing_input):
        return RouterClientOutput(
            payload=self.payload,
            provider="fake-vllm-router",
            raw_content='{"mode":"occasion_outfit"}' if isinstance(self.payload, dict) else "[]",
        )


class RoutingPipelineIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def build_dispatcher(self, *, payload) -> CommandDispatcher:
        conversation_router = ConversationRouter(
            router_client=FakeRouterClient(payload=payload),
        )
        return CommandDispatcher(
            conversation_router=conversation_router,
            conversation_state_policy=ConversationStatePolicy(),
        )

    async def test_router_call_returns_valid_decision(self) -> None:
        dispatcher = self.build_dispatcher(
            payload={
                "mode": "occasion_outfit",
                "confidence": 0.87,
                "needs_clarification": False,
                "missing_slots": [],
                "generation_intent": False,
                "continue_existing_flow": False,
                "should_reset_to_general": False,
                "reasoning_depth": "normal",
            }
        )

        result = await dispatcher.dispatch(
            command=ChatCommand(
                session_id="routing-integration-valid-1",
                locale="en",
                message="What should I wear to a gallery opening tonight?",
            ),
            context=ChatModeContext(),
        )

        self.assertEqual(result.routing.provider, "fake-vllm-router")
        self.assertFalse(result.routing.used_fallback)
        self.assertEqual(result.routing.decision.mode, RoutingMode.OCCASION_OUTFIT)
        self.assertEqual(result.resolution.active_mode, ChatMode.OCCASION_OUTFIT)
        self.assertEqual(result.context.active_mode, ChatMode.OCCASION_OUTFIT)

    async def test_malformed_router_output_degrades_safely(self) -> None:
        dispatcher = self.build_dispatcher(payload=["not-a-json-object"])

        result = await dispatcher.dispatch(
            command=ChatCommand(
                session_id="routing-integration-malformed-1",
                locale="en",
                message="Hello",
            ),
            context=ChatModeContext(),
        )

        self.assertTrue(result.routing.used_fallback)
        self.assertEqual(result.routing.failure_reason, RouterFailureReason.MALFORMED_OUTPUT)
        self.assertTrue(result.routing.validation_errors)
        self.assertEqual(result.routing.decision.mode, RoutingMode.GENERAL_ADVICE)
        self.assertEqual(result.context.active_mode, ChatMode.GENERAL_ADVICE)

    async def test_stale_mode_resets_correctly(self) -> None:
        dispatcher = self.build_dispatcher(
            payload={
                "mode": "general_advice",
                "confidence": 0.82,
                "needs_clarification": False,
                "missing_slots": [],
                "generation_intent": False,
                "continue_existing_flow": False,
                "should_reset_to_general": True,
                "reasoning_depth": "light",
            }
        )
        context = ChatModeContext(
            active_mode=ChatMode.STYLE_EXPLORATION,
            flow_state=FlowState.COMPLETED,
            current_style_id="stale-style",
            current_style_name="Stale Style",
            last_generation_prompt="stale prompt",
            last_generated_outfit_summary="stale summary",
        )

        result = await dispatcher.dispatch(
            command=ChatCommand(
                session_id="routing-integration-stale-1",
                locale="en",
                message="Thanks, now just give me general styling advice",
            ),
            context=context,
        )

        self.assertEqual(result.routing.decision.mode, RoutingMode.GENERAL_ADVICE)
        self.assertTrue(result.resolution.started_new_mode)
        self.assertEqual(result.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(result.context.flow_state, FlowState.IDLE)
        self.assertIsNone(result.context.current_style_id)
        self.assertIsNone(result.context.current_style_name)
        self.assertIsNone(result.context.last_generation_prompt)
        self.assertIsNone(result.context.last_generated_outfit_summary)

    async def test_explicit_style_button_always_routes_to_style_exploration(self) -> None:
        dispatcher = self.build_dispatcher(payload=["malformed"])

        result = await dispatcher.dispatch(
            command=ChatCommand(
                session_id="routing-integration-style-button-1",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                metadata={"source": "quick_action"},
            ),
            context=ChatModeContext(),
        )

        self.assertTrue(result.routing.used_fallback)
        self.assertEqual(result.routing.fallback_rule, "explicit_style_button")
        self.assertEqual(result.routing.decision.mode, RoutingMode.STYLE_EXPLORATION)
        self.assertTrue(result.routing.decision.generation_intent)
        self.assertEqual(result.resolution.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertEqual(result.context.active_mode, ChatMode.STYLE_EXPLORATION)
