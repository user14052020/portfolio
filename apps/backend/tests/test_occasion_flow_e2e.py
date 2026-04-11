import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import OccasionExtractionOutput
from app.application.stylist_chat.results.decision_result import DecisionType
from app.domain.chat_modes import ChatMode, FlowState

try:
    from test_stylist_orchestrator import build_test_orchestrator
except ModuleNotFoundError:
    from tests.test_stylist_orchestrator import build_test_orchestrator


class OccasionFlowE2ETests(unittest.IsolatedAsyncioTestCase):
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

    async def test_day_wedding_in_summer_goes_from_start_to_generation(self) -> None:
        start = await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-1",
                locale="en",
                message="What should I wear to an event?",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
                client_message_id="occasion-e2e-1-start",
            )
        )

        self.assertEqual(start.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.flow_state, FlowState.AWAITING_OCCASION_DETAILS)

        self.reasoner.route = "text_and_generation"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            event_type="wedding",
            time_of_day="day",
            season_or_weather="summer",
            desired_impression="elegant",
        )

        followup = await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-1",
                locale="en",
                message="A daytime wedding in summer, I want to look elegant",
                user_message_id=2,
                client_message_id="occasion-e2e-1-followup",
                command_id="occasion-e2e-1-followup",
            )
        )

        self.assertEqual(followup.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(followup.job_id, "job-1")
        self.assertEqual(self.context_store.context.active_mode, ChatMode.OCCASION_OUTFIT)
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)

    async def test_exhibition_then_slot_specific_clarification_then_generation(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-2",
                locale="en",
                message="What should I wear to an event?",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
                client_message_id="occasion-e2e-2-start",
            )
        )

        self.reasoner.occasion_output = OccasionExtractionOutput(event_type="exhibition")
        clarification = await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-2",
                locale="en",
                message="It is for an exhibition",
                user_message_id=2,
                client_message_id="occasion-e2e-2-followup-1",
            )
        )

        self.assertEqual(clarification.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.flow_state, FlowState.AWAITING_OCCASION_CLARIFICATION)
        self.assertIn("time of day", (clarification.text_reply or "").lower())

        self.reasoner.route = "text_and_generation"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            time_of_day="evening",
            season_or_weather="autumn",
            dress_code="smart casual",
        )
        generation = await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-2",
                locale="en",
                message="In the evening during autumn, smart casual",
                user_message_id=3,
                client_message_id="occasion-e2e-2-followup-2",
            )
        )

        self.assertEqual(generation.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(generation.job_id, "job-1")
        self.assertEqual(self.context_store.context.active_mode, ChatMode.OCCASION_OUTFIT)
        self.assertEqual(self.context_store.context.occasion_context.event_type, "exhibition")

    async def test_precise_followup_stays_in_same_mode_and_generates(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-3",
                locale="en",
                message="What should I wear to an event?",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
                client_message_id="occasion-e2e-3-start",
            )
        )

        self.reasoner.occasion_output = OccasionExtractionOutput(event_type="conference")
        clarification = await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-3",
                locale="en",
                message="Conference",
                user_message_id=2,
                client_message_id="occasion-e2e-3-followup-1",
            )
        )

        self.assertEqual(clarification.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.OCCASION_OUTFIT)

        self.reasoner.route = "text_and_generation"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            time_of_day="day",
            season_or_weather="autumn",
            desired_impression="polished",
        )
        followup = await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-3",
                locale="en",
                message="During the day in autumn, I want to look polished",
                user_message_id=3,
                client_message_id="occasion-e2e-3-followup-2",
            )
        )

        self.assertEqual(followup.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(followup.job_id, "job-1")
        self.assertEqual(self.context_store.context.active_mode, ChatMode.OCCASION_OUTFIT)
        self.assertNotEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)

    async def test_repeated_followup_creates_only_one_job(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-4",
                locale="en",
                message="What should I wear to an event?",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
                client_message_id="occasion-e2e-4-start",
            )
        )

        self.reasoner.route = "text_and_generation"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            event_type="wedding",
            time_of_day="day",
            season_or_weather="summer",
            desired_impression="elegant",
        )

        first = await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-4",
                locale="en",
                message="A daytime wedding in summer, I want to look elegant",
                user_message_id=2,
                client_message_id="occasion-e2e-4-followup",
                command_id="occasion-e2e-4-followup",
            )
        )
        second = await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-4",
                locale="en",
                message="A daytime wedding in summer, I want to look elegant",
                user_message_id=2,
                client_message_id="occasion-e2e-4-followup",
                command_id="occasion-e2e-4-followup",
            )
        )

        self.assertEqual(first.job_id, "job-1")
        self.assertEqual(second.job_id, "job-1")
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_queue_failure_returns_recoverable_response(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-5",
                locale="en",
                message="What should I wear to an event?",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
                client_message_id="occasion-e2e-5-start",
            )
        )

        self.scheduler.fail_next = True
        self.reasoner.route = "text_and_generation"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            event_type="conference",
            time_of_day="day",
            season_or_weather="autumn",
            dress_code="smart casual",
        )

        response = await self.run_command(
            ChatCommand(
                session_id="occasion-e2e-5",
                locale="en",
                message="Conference during the day in autumn, smart casual",
                user_message_id=2,
                client_message_id="occasion-e2e-5-followup",
            )
        )

        self.assertEqual(response.decision_type, DecisionType.ERROR_RECOVERABLE)
        self.assertEqual(response.error_code, "generation_enqueue_failed")
        self.assertEqual(self.context_store.context.flow_state, FlowState.RECOVERABLE_ERROR)
