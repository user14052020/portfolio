import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionType
from app.domain.chat_modes import ChatMode, FlowState

try:
    from test_stylist_orchestrator import build_test_orchestrator
except ModuleNotFoundError:
    from tests.test_stylist_orchestrator import build_test_orchestrator


class StyleExplorationIntegrationTests(unittest.IsolatedAsyncioTestCase):
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
        self.reasoner.route = "text_and_generation"

    async def run_style_command(self, *, session_id: str, message_id: int):
        return await self.orchestrator.handle(
            command=ChatCommand(
                session_id=session_id,
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=message_id,
                client_message_id=f"{session_id}-msg-{message_id}",
                command_id=f"{session_id}-cmd-{message_id}",
            )
        )

    async def test_first_style_exploration_with_empty_history_generates_immediately(self) -> None:
        response = await self.run_style_command(session_id="style-int-1", message_id=1)

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(response.job_id, "job-1")
        self.assertEqual(self.context_store.context.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)
        self.assertEqual(len(self.context_store.context.style_history), 1)

    async def test_second_style_exploration_uses_recent_history_in_reasoning_context(self) -> None:
        await self.run_style_command(session_id="style-int-2", message_id=1)
        await self.run_style_command(session_id="style-int-2", message_id=2)

        previous_directions = self.reasoner.last_reasoning_input["previous_style_directions"]

        self.assertGreaterEqual(len(previous_directions), 1)
        self.assertEqual(previous_directions[-1]["style_id"], "artful-minimalism")
        self.assertEqual(self.context_store.context.style_history[-1].style_id, "soft-retro-prep")

    async def test_repeat_prevention_on_palette_is_propagated_to_generation_payload(self) -> None:
        await self.run_style_command(session_id="style-int-3", message_id=1)
        await self.run_style_command(session_id="style-int-3", message_id=2)

        metadata = self.scheduler.enqueued[-1].metadata
        constraints = metadata["anti_repeat_constraints"]

        self.assertEqual(constraints["avoid_palette"], ["chalk", "charcoal"])
        self.assertEqual(self.context_store.context.style_history[-1].palette, ["camel", "cream"])

    async def test_repeat_prevention_on_hero_garments_is_propagated_to_generation_payload(self) -> None:
        await self.run_style_command(session_id="style-int-4", message_id=1)
        await self.run_style_command(session_id="style-int-4", message_id=2)

        metadata = self.scheduler.enqueued[-1].metadata
        constraints = metadata["anti_repeat_constraints"]

        self.assertEqual(constraints["avoid_hero_garments"], ["structured coat"])
        self.assertEqual(self.context_store.context.style_history[-1].hero_garments, ["oxford shirt"])

    async def test_constraints_and_style_metadata_reach_generation_payload(self) -> None:
        await self.run_style_command(session_id="style-int-5", message_id=1)
        response = await self.run_style_command(session_id="style-int-5", message_id=2)

        metadata = self.scheduler.enqueued[-1].metadata

        self.assertEqual(response.generation_payload.metadata["style_name"], "Soft Retro Prep")
        self.assertEqual(metadata["style_name"], "Soft Retro Prep")
        self.assertEqual(metadata["visual_preset"], "airy_catalog")
        self.assertTrue(metadata["semantic_constraints_hash"])
        self.assertTrue(metadata["visual_constraints_hash"])
        self.assertGreaterEqual(len(metadata["previous_style_directions"]), 1)

    async def test_style_flow_saves_selection_and_enqueue_checkpoints(self) -> None:
        await self.run_style_command(session_id="style-int-6", message_id=1)

        self.assertGreaterEqual(len(self.checkpoint_writer.saved_contexts), 3)
        self.assertEqual(self.checkpoint_writer.saved_contexts[0].flow_state, FlowState.READY_FOR_GENERATION)
        self.assertEqual(self.checkpoint_writer.saved_contexts[-1].flow_state, FlowState.GENERATION_QUEUED)

