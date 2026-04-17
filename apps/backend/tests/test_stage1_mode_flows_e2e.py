import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionType
from app.domain.chat_modes import ChatMode, FlowState
from app.models.enums import GenerationStatus

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

    async def test_hello_never_starts_generation(self) -> None:
        self.reasoner.route = "text_only"

        response = await self.run_command(
            ChatCommand(
                session_id="stage1-e2e-hello",
                locale="ru",
                message="привет",
                user_message_id=1,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_ONLY)
        self.assertIsNone(response.job_id)
        self.assertFalse(response.can_offer_visualization)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_style_button_is_a_valid_generation_trigger(self) -> None:
        self.reasoner.route = "text_and_generation"

        response = await self.run_command(
            ChatCommand(
                session_id="stage1-e2e-style-button",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
                metadata={"source": "quick_action"},
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(response.job_id, "job-1")
        self.assertEqual(self.context_store.context.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)

    async def test_post_style_generation_free_text_returns_to_general_dialog(self) -> None:
        self.reasoner.route = "text_and_generation"
        generated = await self.run_command(
            ChatCommand(
                session_id="stage1-e2e-reset",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
                metadata={"source": "quick_action"},
            )
        )

        self.assertEqual(generated.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.scheduler.job_statuses["job-1"] = GenerationStatus.COMPLETED
        self.reasoner.route = "text_only"

        followup = await self.run_command(
            ChatCommand(
                session_id="stage1-e2e-reset",
                locale="en",
                message="What shoes would work for everyday wear?",
                user_message_id=2,
            )
        )

        self.assertEqual(followup.decision_type, DecisionType.TEXT_ONLY)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.COMPLETED)
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_generation_can_start_from_confirmed_cta(self) -> None:
        self.reasoner.route = "text_and_generation"
        first = await self.run_command(
            ChatCommand(
                session_id="stage1-e2e-cta",
                locale="en",
                message="How can I modernize a white shirt?",
                user_message_id=1,
            )
        )

        self.assertEqual(first.decision_type, DecisionType.TEXT_ONLY)
        self.assertTrue(first.can_offer_visualization)
        self.assertEqual(len(self.scheduler.enqueued), 0)

        second = await self.run_command(
            ChatCommand(
                session_id="stage1-e2e-cta",
                locale="en",
                message="Confirm the visualization",
                user_message_id=2,
                metadata={"source": "visualization_cta", "visualization_type": "flat_lay_reference"},
            )
        )

        self.assertEqual(second.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(second.job_id, "job-1")
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_generation_can_start_from_explicit_visual_text_request(self) -> None:
        self.reasoner.route = "text_and_generation"

        response = await self.run_command(
            ChatCommand(
                session_id="stage1-e2e-explicit",
                locale="ru",
                message="визуализируй мягкий интеллектуальный образ на вечернюю выставку",
                user_message_id=1,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(response.job_id, "job-1")
        self.assertEqual(len(self.scheduler.enqueued), 1)
