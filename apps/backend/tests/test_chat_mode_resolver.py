import unittest

from app.domain.chat_context import ChatModeContext, CommandContext
from app.domain.chat_modes import ChatMode, FlowState
from app.services.chat_mode_resolver import chat_mode_resolver


class ChatModeResolverTests(unittest.TestCase):
    def test_idle_session_defaults_to_general_advice(self) -> None:
        resolution = chat_mode_resolver.resolve(
            context=ChatModeContext(),
            requested_intent=None,
            command_name=None,
            command_step=None,
            metadata=None,
        )

        self.assertEqual(resolution.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertFalse(resolution.continue_existing_flow)

    def test_completed_command_flow_continues_same_mode_without_requested_intent(self) -> None:
        context = ChatModeContext(
            active_mode=ChatMode.GARMENT_MATCHING,
            requested_intent=ChatMode.GARMENT_MATCHING,
            flow_state=FlowState.COMPLETED,
            command_context=CommandContext(
                command_name="garment_matching",
                command_step="entry",
                metadata={"source": "quick_action"},
            ),
        )

        resolution = chat_mode_resolver.resolve(
            context=context,
            requested_intent=None,
            command_name=None,
            command_step=None,
            metadata=None,
        )

        self.assertEqual(resolution.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertFalse(resolution.started_new_mode)
        self.assertTrue(resolution.continue_existing_flow)
        self.assertIsNotNone(resolution.command_context)
        self.assertEqual(resolution.command_context.command_name, "garment_matching")

    def test_requested_intent_switches_mode_and_captures_command_context(self) -> None:
        context = ChatModeContext(
            active_mode=ChatMode.GENERAL_ADVICE,
            flow_state=FlowState.COMPLETED,
        )

        resolution = chat_mode_resolver.resolve(
            context=context,
            requested_intent=ChatMode.OCCASION_OUTFIT,
            command_name="occasion_outfit",
            command_step="entry",
            metadata={"source": "quick_action"},
        )

        self.assertEqual(resolution.active_mode, ChatMode.OCCASION_OUTFIT)
        self.assertTrue(resolution.started_new_mode)
        self.assertFalse(resolution.continue_existing_flow)
        self.assertIsNotNone(resolution.command_context)
        self.assertEqual(resolution.command_context.command_name, "occasion_outfit")
        self.assertEqual(resolution.command_context.command_step, "entry")
