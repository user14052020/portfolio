import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionType
from app.domain.chat_modes import ChatMode, FlowState

try:
    from test_stylist_orchestrator import build_test_orchestrator
except ModuleNotFoundError:
    from tests.test_stylist_orchestrator import build_test_orchestrator


class StyleExplorationFlowE2ETests(unittest.IsolatedAsyncioTestCase):
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
                metadata={"source": "quick_action"},
            )
        )

    async def test_first_style_exploration_goes_to_generation(self) -> None:
        response = await self.run_style_command(session_id="style-e2e-1", message_id=1)

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(response.job_id, "job-1")
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)

    async def test_second_run_changes_palette_and_silhouette(self) -> None:
        await self.run_style_command(session_id="style-e2e-2", message_id=1)
        await self.run_style_command(session_id="style-e2e-2", message_id=2)

        previous_style = self.context_store.context.style_history[-2]
        current_style = self.context_store.context.style_history[-1]

        self.assertNotEqual(current_style.style_id, previous_style.style_id)
        self.assertNotEqual(current_style.palette, previous_style.palette)
        self.assertNotEqual(current_style.silhouette_family, previous_style.silhouette_family)

    async def test_third_run_changes_visual_preset_when_style_library_repeats(self) -> None:
        await self.run_style_command(session_id="style-e2e-3", message_id=1)
        await self.run_style_command(session_id="style-e2e-3", message_id=2)
        response = await self.run_style_command(session_id="style-e2e-3", message_id=3)

        previous_style = self.context_store.context.style_history[-2]
        current_style = self.context_store.context.style_history[-1]

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(current_style.style_id, "artful-minimalism")
        self.assertNotEqual(current_style.visual_preset, previous_style.visual_preset)
        self.assertEqual(response.generation_payload.visual_preset, current_style.visual_preset)

    async def test_provider_fallback_preserves_constraints_and_style_telemetry(self) -> None:
        await self.run_style_command(session_id="style-e2e-4", message_id=1)
        self.reasoner.raise_error = True

        response = await self.run_style_command(session_id="style-e2e-4", message_id=2)

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertTrue(response.telemetry["fallback_used"])
        self.assertTrue(response.telemetry["semantic_constraints_hash"])
        self.assertTrue(response.telemetry["visual_constraints_hash"])
        self.assertTrue(response.generation_payload.metadata["anti_repeat_constraints"]["avoid_palette"])

    async def test_refresh_retry_path_does_not_lose_style_history(self) -> None:
        await self.run_style_command(session_id="style-e2e-5", message_id=1)
        await self.run_style_command(session_id="style-e2e-5", message_id=2)
        response = await self.run_style_command(session_id="style-e2e-5", message_id=3)
        previous_directions = self.reasoner.last_reasoning_input["previous_style_directions"]

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertEqual(len(previous_directions), 2)
        self.assertGreaterEqual(len(self.context_store.context.style_history), 2)
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)
