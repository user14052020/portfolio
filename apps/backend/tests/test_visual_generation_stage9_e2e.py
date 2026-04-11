import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_modes import ChatMode, FlowState
from tests.test_stylist_orchestrator import build_test_orchestrator


class VisualGenerationStage9E2ETests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        (
            self.orchestrator,
            self.context_store,
            self.reasoner,
            self.scheduler,
            _event_logger,
            _metrics_recorder,
            _checkpoint_writer,
        ) = build_test_orchestrator()

    async def run_command(self, command: ChatCommand):
        return await self.orchestrator.handle(command=command)

    async def test_garment_matching_enqueues_anchor_centric_visual_plan(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="stage9-garment-1",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
            )
        )
        self.reasoner.route = "text_and_generation"

        response = await self.run_command(
            ChatCommand(
                session_id="stage9-garment-1",
                locale="en",
                message="black leather jacket",
                user_message_id=2,
            )
        )

        self.assertEqual(response.job_id, "job-1")
        request = self.scheduler.enqueued[-1]
        self.assertEqual(request.workflow_name, "garment_matching_variation")
        self.assertEqual(request.visual_generation_plan["anchor_garment_centrality"], "high")
        self.assertEqual(request.generation_metadata["workflow_name"], "garment_matching_variation")

    async def test_style_exploration_twice_rotates_visual_preset_background_and_layout(self) -> None:
        self.reasoner.route = "text_and_generation"

        first = await self.run_command(
            ChatCommand(
                session_id="stage9-style-1",
                locale="en",
                message="Show me a fresh style direction",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
            )
        )
        self.assertEqual(first.job_id, "job-1")
        first_request = self.scheduler.enqueued[-1]
        self.context_store.context.current_job_id = None
        self.context_store.context.flow_state = FlowState.COMPLETED

        second = await self.run_command(
            ChatCommand(
                session_id="stage9-style-1",
                locale="en",
                message="Try another one",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=2,
                command_id="stage9-style-1-second",
            )
        )
        self.assertEqual(second.job_id, "job-2")
        second_request = self.scheduler.enqueued[-1]

        self.assertNotEqual(
            second_request.visual_generation_plan["visual_preset_id"],
            first_request.visual_generation_plan["visual_preset_id"],
        )
        self.assertNotEqual(
            second_request.visual_generation_plan["background_family"],
            first_request.visual_generation_plan["background_family"],
        )
        self.assertNotEqual(
            second_request.visual_generation_plan["layout_archetype"],
            first_request.visual_generation_plan["layout_archetype"],
        )

    async def test_occasion_outfit_enqueues_practical_visual_plan(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="stage9-occasion-1",
                locale="en",
                message="Need an outfit for an event",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
            )
        )
        self.reasoner.route = "text_and_generation"

        response = await self.run_command(
            ChatCommand(
                session_id="stage9-occasion-1",
                locale="en",
                message="Conference during the day in autumn, smart casual",
                user_message_id=2,
            )
        )

        self.assertEqual(response.job_id, "job-1")
        request = self.scheduler.enqueued[-1]
        self.assertEqual(request.workflow_name, "occasion_outfit_variation")
        self.assertEqual(request.visual_generation_plan["practical_coherence"], "high")
        self.assertEqual(request.visual_generation_plan["layout_archetype"], "practical dressing board")

    async def test_anti_repeat_constraints_survive_until_generation_schedule_payload(self) -> None:
        self.reasoner.route = "text_and_generation"

        await self.run_command(
            ChatCommand(
                session_id="stage9-style-anti-repeat-1",
                locale="en",
                message="Try another style direction",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
            )
        )

        request = self.scheduler.enqueued[-1]
        self.assertTrue(request.visual_generation_plan["diversity_profile"])
        self.assertEqual(
            request.visual_generation_plan["diversity_profile"],
            request.generation_metadata["diversity_constraints"],
        )

    async def test_generation_metadata_supports_replay_and_debug(self) -> None:
        self.reasoner.route = "text_and_generation"

        response = await self.run_command(
            ChatCommand(
                session_id="stage9-style-debug-1",
                locale="en",
                message="Give me a new style direction",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
            )
        )

        self.assertEqual(response.job_id, "job-1")
        metadata = self.scheduler.enqueued[-1].generation_metadata
        self.assertTrue(metadata["final_prompt"])
        self.assertEqual(metadata["negative_prompt"], "avoid clutter")
        self.assertTrue(metadata["workflow_name"])
        self.assertTrue(metadata["visual_preset_id"])
        self.assertTrue(metadata["style_id"])
