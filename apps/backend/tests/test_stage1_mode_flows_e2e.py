import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionType
from app.domain.chat_modes import ChatMode, FlowState

try:
    from test_stylist_orchestrator import build_test_orchestrator
except ModuleNotFoundError:
    from tests.test_stylist_orchestrator import build_test_orchestrator


class Stage1ModeFlowsE2ETests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        (
            self.orchestrator,
            self.context_store,
            self.reasoner,
            self.scheduler,
            self.event_logger,
            self.metrics_recorder,
            self.checkpoint_writer,
        ) = build_test_orchestrator()

    async def run_command(self, command: ChatCommand):
        return await self.orchestrator.handle(command=command)

    async def test_general_advice_followup_stays_in_general_mode(self) -> None:
        self.reasoner.route = "text_only"
        first = await self.run_command(
            ChatCommand(
                session_id="stage1-general-1",
                locale="en",
                message="How can I modernize a white shirt?",
                user_message_id=1,
                client_message_id="stage1-general-1-msg-1",
            )
        )
        second = await self.run_command(
            ChatCommand(
                session_id="stage1-general-1",
                locale="en",
                message="And what shoes would work with it?",
                user_message_id=2,
                client_message_id="stage1-general-1-msg-2",
            )
        )

        self.assertEqual(first.decision_type, DecisionType.TEXT_ONLY)
        self.assertEqual(second.decision_type, DecisionType.TEXT_ONLY)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.COMPLETED)
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_general_advice_can_switch_explicitly_into_command_mode(self) -> None:
        self.reasoner.route = "text_only"
        await self.run_command(
            ChatCommand(
                session_id="stage1-transition-1",
                locale="en",
                message="How can I modernize a white shirt?",
                user_message_id=1,
                client_message_id="stage1-transition-1-msg-1",
            )
        )

        command_response = await self.run_command(
            ChatCommand(
                session_id="stage1-transition-1",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=2,
                client_message_id="stage1-transition-1-msg-2",
            )
        )

        self.assertEqual(command_response.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertEqual(self.context_store.context.flow_state, FlowState.AWAITING_ANCHOR_GARMENT)

    async def test_style_exploration_second_run_uses_history_and_does_not_fall_to_general_chat(self) -> None:
        self.reasoner.route = "text_and_generation"
        first = await self.run_command(
            ChatCommand(
                session_id="stage1-style-1",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
                client_message_id="stage1-style-1-msg-1",
            )
        )
        second = await self.run_command(
            ChatCommand(
                session_id="stage1-style-1",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=2,
                client_message_id="stage1-style-1-msg-2",
            )
        )

        self.assertEqual(first.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(second.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertNotEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertGreaterEqual(len(self.context_store.context.style_history), 2)
        self.assertNotEqual(
            self.context_store.context.style_history[-1].style_id,
            self.context_store.context.style_history[-2].style_id,
        )
