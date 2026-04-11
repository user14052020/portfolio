import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionType
from app.domain.chat_modes import ChatMode, FlowState

try:
    from test_stylist_orchestrator import build_test_orchestrator
except ModuleNotFoundError:
    from tests.test_stylist_orchestrator import build_test_orchestrator


class GarmentFlowE2ETests(unittest.IsolatedAsyncioTestCase):
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

    async def test_black_leather_jacket_goes_from_start_to_generation(self) -> None:
        start = await self.run_command(
            ChatCommand(
                session_id="garment-e2e-1",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
                client_message_id="garment-e2e-1-start",
            )
        )

        self.assertEqual(start.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(self.context_store.context.flow_state, FlowState.AWAITING_ANCHOR_GARMENT)

        self.reasoner.route = "text_and_generation"
        followup = await self.run_command(
            ChatCommand(
                session_id="garment-e2e-1",
                locale="en",
                message="black leather jacket",
                user_message_id=2,
                client_message_id="garment-e2e-1-followup",
                command_id="garment-e2e-1-followup",
            )
        )

        self.assertEqual(followup.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(followup.job_id, "job-1")
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)

    async def test_shirt_then_white_linen_clarification_then_generation(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="garment-e2e-2",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
                client_message_id="garment-e2e-2-start",
            )
        )

        clarification = await self.run_command(
            ChatCommand(
                session_id="garment-e2e-2",
                locale="en",
                message="shirt",
                user_message_id=2,
                client_message_id="garment-e2e-2-followup-1",
            )
        )

        self.assertEqual(clarification.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(
            self.context_store.context.flow_state,
            FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION,
        )

        self.reasoner.route = "text_and_generation"
        generation = await self.run_command(
            ChatCommand(
                session_id="garment-e2e-2",
                locale="en",
                message="white linen",
                user_message_id=3,
                client_message_id="garment-e2e-2-followup-2",
                command_id="garment-e2e-2-followup-2",
            )
        )

        self.assertEqual(generation.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(generation.job_id, "job-1")
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertEqual(self.context_store.context.anchor_garment.garment_type, "shirt")
        self.assertEqual(self.context_store.context.anchor_garment.material, "linen")

    async def test_asset_only_followup_requires_clarification_then_generates(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="garment-e2e-3",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
                client_message_id="garment-e2e-3-start",
            )
        )

        clarification = await self.run_command(
            ChatCommand(
                session_id="garment-e2e-3",
                locale="en",
                message=None,
                asset_id="asset-1",
                asset_metadata={"original_filename": "shirt-reference.jpg"},
                user_message_id=2,
                client_message_id="garment-e2e-3-followup-1",
            )
        )

        self.assertEqual(clarification.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(
            self.context_store.context.flow_state,
            FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION,
        )

        self.reasoner.route = "text_and_generation"
        generation = await self.run_command(
            ChatCommand(
                session_id="garment-e2e-3",
                locale="en",
                message="white linen",
                asset_id="asset-1",
                asset_metadata={"original_filename": "shirt-reference.jpg"},
                user_message_id=3,
                client_message_id="garment-e2e-3-followup-2",
                command_id="garment-e2e-3-followup-2",
            )
        )

        self.assertEqual(generation.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(generation.job_id, "job-1")
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertEqual(self.context_store.context.anchor_garment.garment_type, "shirt")
        self.assertEqual(self.context_store.context.anchor_garment.material, "linen")

    async def test_repeated_followup_creates_only_one_job(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="garment-e2e-4",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
                client_message_id="garment-e2e-4-start",
            )
        )

        self.reasoner.route = "text_and_generation"
        first = await self.run_command(
            ChatCommand(
                session_id="garment-e2e-4",
                locale="en",
                message="black leather jacket",
                user_message_id=2,
                client_message_id="garment-e2e-4-followup",
                command_id="garment-e2e-4-followup",
            )
        )
        second = await self.run_command(
            ChatCommand(
                session_id="garment-e2e-4",
                locale="en",
                message="black leather jacket",
                user_message_id=2,
                client_message_id="garment-e2e-4-followup",
                command_id="garment-e2e-4-followup",
            )
        )

        self.assertEqual(first.job_id, "job-1")
        self.assertEqual(second.job_id, "job-1")
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_queue_failure_returns_recoverable_response(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="garment-e2e-5",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
                client_message_id="garment-e2e-5-start",
            )
        )

        self.scheduler.fail_next = True
        self.reasoner.route = "text_and_generation"
        response = await self.run_command(
            ChatCommand(
                session_id="garment-e2e-5",
                locale="en",
                message="black leather jacket",
                user_message_id=2,
                client_message_id="garment-e2e-5-followup",
            )
        )

        self.assertEqual(response.decision_type, DecisionType.ERROR_RECOVERABLE)
        self.assertEqual(response.error_code, "generation_enqueue_failed")
        self.assertEqual(self.context_store.context.flow_state, FlowState.RECOVERABLE_ERROR)
