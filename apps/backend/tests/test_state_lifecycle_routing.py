import unittest

from app.application.product_behavior.services.conversation_state_policy import ConversationStatePolicy
from app.application.product_behavior.services.session_flow_state_service import SessionFlowStateService
from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import ConversationRoutingResult
from app.application.stylist_chat.orchestrator.command_dispatcher import CommandDispatcher
from app.domain.chat_context import ChatModeContext, GenerationIntent
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.routing import ConversationRouterContext, RoutingDecision, RoutingInput, RoutingMode
from app.models.enums import GenerationStatus


class FakeConversationRouter:
    def __init__(self, *, decision: RoutingDecision) -> None:
        self.decision = decision

    async def route(self, *, command: ChatCommand, context: ChatModeContext) -> ConversationRoutingResult:
        return ConversationRoutingResult(
            decision=self.decision,
            routing_input=RoutingInput(
                user_message=command.normalized_message(),
                active_mode=RoutingMode(context.active_mode.value),
                flow_state=context.flow_state.value,
                pending_slots=[],
                recent_messages=[],
                last_ui_action=None,
                profile_hint_present=False,
            ),
            routing_context=ConversationRouterContext(
                active_mode=RoutingMode(context.active_mode.value),
                flow_state=context.flow_state.value,
                pending_slots=[],
                recent_messages=[],
                last_ui_action=None,
                last_generation_completed=context.flow_state == FlowState.COMPLETED,
                last_visual_cta_offered=False,
                profile_context_present=False,
            ),
        )


class RoutingLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_continue_existing_flow_true_keeps_active_flow_state(self) -> None:
        dispatcher = CommandDispatcher(
            conversation_router=FakeConversationRouter(
                decision=RoutingDecision(
                    mode=RoutingMode.OCCASION_OUTFIT,
                    confidence=0.91,
                    continue_existing_flow=True,
                )
            ),
            conversation_state_policy=ConversationStatePolicy(),
        )
        context = ChatModeContext(
            active_mode=ChatMode.OCCASION_OUTFIT,
            flow_state=FlowState.AWAITING_OCCASION_DETAILS,
            current_style_id="active-style",
            current_style_name="Active Style",
        )

        result = await dispatcher.dispatch(
            command=ChatCommand(
                session_id="lifecycle-continue-1",
                locale="en",
                message="It's for a rooftop dinner next Friday",
            ),
            context=context,
        )

        self.assertFalse(result.resolution.started_new_mode)
        self.assertTrue(result.resolution.continue_existing_flow)
        self.assertEqual(result.context.active_mode, ChatMode.OCCASION_OUTFIT)
        self.assertEqual(result.context.flow_state, FlowState.AWAITING_OCCASION_DETAILS)
        self.assertEqual(result.context.current_style_id, "active-style")
        self.assertEqual(result.context.current_style_name, "Active Style")

    async def test_same_mode_without_continue_restarts_completed_flow_and_clears_stale_fields(self) -> None:
        dispatcher = CommandDispatcher(
            conversation_router=FakeConversationRouter(
                decision=RoutingDecision(
                    mode=RoutingMode.OCCASION_OUTFIT,
                    confidence=0.88,
                    continue_existing_flow=False,
                )
            ),
            conversation_state_policy=ConversationStatePolicy(),
        )
        context = ChatModeContext(
            active_mode=ChatMode.OCCASION_OUTFIT,
            flow_state=FlowState.COMPLETED,
            current_style_id="stale-style",
            current_style_name="Stale Style",
            last_generation_prompt="old prompt",
            last_generated_outfit_summary="old summary",
        )

        result = await dispatcher.dispatch(
            command=ChatCommand(
                session_id="lifecycle-restart-1",
                locale="en",
                message="Need another outfit for a different evening event",
            ),
            context=context,
        )

        self.assertTrue(result.resolution.started_new_mode)
        self.assertFalse(result.resolution.continue_existing_flow)
        self.assertEqual(result.context.active_mode, ChatMode.OCCASION_OUTFIT)
        self.assertEqual(result.context.flow_state, FlowState.IDLE)
        self.assertIsNone(result.context.current_style_id)
        self.assertIsNone(result.context.current_style_name)
        self.assertIsNone(result.context.last_generation_prompt)
        self.assertIsNone(result.context.last_generated_outfit_summary)

    async def test_router_reset_to_general_clears_stale_completed_mode_state(self) -> None:
        dispatcher = CommandDispatcher(
            conversation_router=FakeConversationRouter(
                decision=RoutingDecision(
                    mode=RoutingMode.GENERAL_ADVICE,
                    confidence=0.83,
                    continue_existing_flow=False,
                    should_reset_to_general=True,
                )
            ),
            conversation_state_policy=ConversationStatePolicy(),
        )
        context = ChatModeContext(
            active_mode=ChatMode.OCCASION_OUTFIT,
            flow_state=FlowState.COMPLETED,
            current_style_id="stale-style",
            current_style_name="Stale Style",
            last_generation_prompt="old prompt",
            last_generated_outfit_summary="old summary",
            last_retrieved_knowledge_refs=[{"id": "stale-ref"}],
        )

        result = await dispatcher.dispatch(
            command=ChatCommand(
                session_id="lifecycle-general-reset-1",
                locale="en",
                message="Thanks, now can you explain how to dress better in general?",
            ),
            context=context,
        )

        self.assertTrue(result.resolution.started_new_mode)
        self.assertFalse(result.resolution.continue_existing_flow)
        self.assertEqual(result.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(result.context.flow_state, FlowState.IDLE)
        self.assertIsNone(result.context.current_style_id)
        self.assertIsNone(result.context.current_style_name)
        self.assertIsNone(result.context.last_generation_prompt)
        self.assertIsNone(result.context.last_generated_outfit_summary)
        self.assertEqual(result.context.last_retrieved_knowledge_refs, [])

    def test_completed_visual_flow_reset_to_general_clears_mode_specific_state(self) -> None:
        service = SessionFlowStateService()
        context = ChatModeContext(
            active_mode=ChatMode.OCCASION_OUTFIT,
            flow_state=FlowState.GENERATION_IN_PROGRESS,
            current_job_id="job-42",
            current_style_id="style-42",
            current_style_name="Editorial Evening",
            last_generation_prompt="prompt-42",
            last_generated_outfit_summary="summary-42",
            last_retrieved_knowledge_refs=[{"id": "ref-1"}],
            generation_intent=GenerationIntent(
                mode=ChatMode.OCCASION_OUTFIT,
                trigger="visualization_cta",
                reason="explicit confirmation",
                must_generate=True,
            ),
        )

        result = service.sync_generation_status(
            context=context,
            generation_status=GenerationStatus.COMPLETED,
        )

        self.assertEqual(result.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(result.flow_state, FlowState.IDLE)
        self.assertIsNone(result.current_job_id)
        self.assertIsNone(result.current_style_id)
        self.assertIsNone(result.current_style_name)
        self.assertIsNone(result.last_generation_prompt)
        self.assertIsNone(result.last_generated_outfit_summary)
        self.assertEqual(result.last_retrieved_knowledge_refs, [])
        self.assertIsNone(result.generation_intent)
