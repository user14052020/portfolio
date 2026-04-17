import unittest

from app.domain.routing import (
    ROUTING_MODES,
    ConversationRouterContext,
    ReasoningDepth,
    RoutingDecision,
    RoutingInput,
    RoutingMode,
)


class RoutingContractsTests(unittest.TestCase):
    def test_routing_input_defaults_to_allowed_modes_from_contract(self) -> None:
        routing_input = RoutingInput(user_message="hello")

        self.assertEqual(routing_input.allowed_modes, list(ROUTING_MODES))
        self.assertEqual(routing_input.active_mode, None)
        self.assertEqual(routing_input.pending_slots, [])
        self.assertEqual(routing_input.recent_messages, [])

    def test_routing_decision_safe_default_is_general_and_non_generating(self) -> None:
        decision = RoutingDecision.safe_default()

        self.assertEqual(decision.mode, RoutingMode.GENERAL_ADVICE)
        self.assertEqual(decision.reasoning_depth, ReasoningDepth.LIGHT)
        self.assertFalse(decision.generation_intent)
        self.assertFalse(decision.continue_existing_flow)
        self.assertFalse(decision.should_reset_to_general)

    def test_conversation_router_context_carries_compact_router_state(self) -> None:
        context = ConversationRouterContext(
            active_mode=RoutingMode.STYLE_EXPLORATION,
            flow_state="generation_in_progress",
            pending_slots=["event_type"],
            last_ui_action="try_other_style",
            last_generation_completed=True,
            last_visual_cta_offered=True,
            profile_context_present=True,
        )

        self.assertEqual(context.active_mode, RoutingMode.STYLE_EXPLORATION)
        self.assertEqual(context.pending_slots, ["event_type"])
        self.assertTrue(context.last_generation_completed)
        self.assertTrue(context.last_visual_cta_offered)
        self.assertTrue(context.profile_context_present)


if __name__ == "__main__":
    unittest.main()
