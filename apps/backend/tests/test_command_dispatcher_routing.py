import unittest

from app.application.product_behavior.services.conversation_state_policy import ConversationStatePolicy
from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import ConversationRoutingResult
from app.application.stylist_chat.orchestrator.command_dispatcher import CommandDispatcher
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.routing import ConversationRouterContext, RoutingDecision, RoutingInput, RoutingMode


class FakeConversationRouter:
    def __init__(self, *, decision: RoutingDecision) -> None:
        self.decision = decision

    async def route(self, *, command: ChatCommand, context: ChatModeContext) -> ConversationRoutingResult:
        return ConversationRoutingResult(
            decision=self.decision,
            routing_input=RoutingInput(
                user_message=command.normalized_message(),
                active_mode=None,
                flow_state=context.flow_state.value,
                pending_slots=[],
                recent_messages=[],
                last_ui_action=None,
                profile_hint_present=False,
            ),
            routing_context=ConversationRouterContext(
                active_mode=None,
                flow_state=context.flow_state.value,
                pending_slots=[],
                recent_messages=[],
                last_ui_action=None,
                last_generation_completed=False,
                last_visual_cta_offered=False,
                profile_context_present=False,
            ),
            provider="fake-router",
        )


class CommandDispatcherRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_dispatch_uses_router_decision_as_primary_mode(self) -> None:
        dispatcher = CommandDispatcher(
            conversation_router=FakeConversationRouter(
                decision=RoutingDecision(
                    mode=RoutingMode.STYLE_EXPLORATION,
                    confidence=0.91,
                )
            ),
            conversation_state_policy=ConversationStatePolicy(),
        )

        result = await dispatcher.dispatch(
            command=ChatCommand(
                session_id="dispatcher-route-1",
                locale="en",
                message="Show me something more experimental",
                requested_intent=ChatMode.GARMENT_MATCHING,
            ),
            context=ChatModeContext(),
        )

        self.assertEqual(result.resolution.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertEqual(result.context.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertEqual(result.context.requested_intent, ChatMode.STYLE_EXPLORATION)

    async def test_dispatch_maps_clarification_only_to_current_mode(self) -> None:
        dispatcher = CommandDispatcher(
            conversation_router=FakeConversationRouter(
                decision=RoutingDecision(
                    mode=RoutingMode.CLARIFICATION_ONLY,
                    confidence=0.77,
                    needs_clarification=True,
                    continue_existing_flow=True,
                )
            ),
            conversation_state_policy=ConversationStatePolicy(),
        )
        context = ChatModeContext(
            active_mode=ChatMode.GARMENT_MATCHING,
            flow_state=FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION,
        )

        result = await dispatcher.dispatch(
            command=ChatCommand(
                session_id="dispatcher-clarification-1",
                locale="en",
                message="It is dark blue wool",
            ),
            context=context,
        )

        self.assertEqual(result.resolution.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertTrue(result.resolution.continue_existing_flow)
        self.assertEqual(result.context.active_mode, ChatMode.GARMENT_MATCHING)
