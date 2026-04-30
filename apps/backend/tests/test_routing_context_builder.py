import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.services.routing_context_builder import RoutingContextBuilder
from app.domain.chat_context import ChatModeContext, CommandContext, ConversationMemoryItem
from app.domain.chat_modes import ChatMode, ClarificationKind, FlowState
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext
from app.domain.product_behavior.entities.visualization_offer import VisualizationOffer


class RoutingContextBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.builder = RoutingContextBuilder()

    def test_build_input_uses_compact_recent_memory_without_orm_dependency(self) -> None:
        command = ChatCommand(session_id="s1", message="hello")
        context = ChatModeContext(
            conversation_memory=[
                ConversationMemoryItem(role="user", content="first user"),
                ConversationMemoryItem(role="assistant", content="first assistant"),
                ConversationMemoryItem(role="system", content="ignored system"),
                ConversationMemoryItem(role="user", content="second user"),
                ConversationMemoryItem(role="assistant", content="second assistant"),
            ]
        )

        routing_input = self.builder.build_input(command=command, context=context)

        self.assertEqual(
            routing_input.recent_messages,
            ["first user", "first assistant", "second user", "second assistant"],
        )

    def test_build_context_maps_current_quick_action_to_try_other_style(self) -> None:
        command = ChatCommand(
            session_id="s1",
            message="",
            command_name="style_exploration",
            command_step="start",
            metadata={"source": "quick_action"},
        )
        context = ChatModeContext(active_mode=ChatMode.GENERAL_ADVICE)

        router_context = self.builder.build_context(command=command, context=context)

        self.assertEqual(router_context.last_ui_action, "try_other_style")

    def test_build_context_uses_previous_visualization_cta_when_current_command_has_no_ui_action(self) -> None:
        command = ChatCommand(session_id="s1", message="привет")
        context = ChatModeContext(
            active_mode=ChatMode.GENERAL_ADVICE,
            command_context=CommandContext(
                command_name="general_advice",
                command_step="confirm_visualization",
                metadata={"source": "visualization_cta"},
            ),
        )

        router_context = self.builder.build_context(command=command, context=context)

        self.assertEqual(router_context.last_ui_action, "confirm_visualization")

    def test_build_context_resolves_pending_slots_from_garment_and_clarification_state(self) -> None:
        command = ChatCommand(session_id="s1", message="help")
        context = ChatModeContext(
            active_mode=ChatMode.GARMENT_MATCHING,
            flow_state=FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION,
            clarification_kind=ClarificationKind.ANCHOR_GARMENT_MISSING_ATTRIBUTES,
            pending_clarification="Describe the garment",
            anchor_garment=AnchorGarment(garment_type="coat"),
        )

        router_context = self.builder.build_context(command=command, context=context)

        self.assertEqual(
            router_context.pending_slots,
            ["color_or_material", "styling_context", "garment_attributes"],
        )

    def test_build_context_resolves_pending_slots_from_occasion_context(self) -> None:
        command = ChatCommand(session_id="s1", message="need an outfit")
        context = ChatModeContext(
            active_mode=ChatMode.OCCASION_OUTFIT,
            flow_state=FlowState.AWAITING_OCCASION_DETAILS,
            occasion_context=OccasionContext(event_type="gallery opening"),
        )

        router_context = self.builder.build_context(command=command, context=context)

        self.assertEqual(
            router_context.pending_slots,
            ["time_of_day", "season", "dress_code", "desired_impression", "occasion_details"],
        )

    def test_build_context_tracks_generation_completion_cta_and_profile_presence(self) -> None:
        command = ChatCommand(
            session_id="s1",
            message="show me more",
            profile_context={"presentation_profile": "androgynous"},
        )
        context = ChatModeContext(
            active_mode=ChatMode.GENERAL_ADVICE,
            flow_state=FlowState.COMPLETED,
            visualization_offer=VisualizationOffer(
                can_offer_visualization=True,
                cta_text="Show flat lay",
                visualization_type="flat_lay_reference",
            ),
        )

        router_context = self.builder.build_context(command=command, context=context)

        self.assertTrue(router_context.last_generation_completed)
        self.assertTrue(router_context.last_visual_cta_offered)
        self.assertTrue(router_context.profile_context_present)

    def test_build_context_treats_session_profile_sources_as_profile_hints(self) -> None:
        command = ChatCommand(
            session_id="s1",
            message="show me more",
            metadata={
                "session_profile_context": {
                    "presentation_profile": "androgynous",
                    "fit_preferences": ["relaxed"],
                }
            },
        )
        context = ChatModeContext(active_mode=ChatMode.GENERAL_ADVICE)

        router_context = self.builder.build_context(command=command, context=context)

        self.assertTrue(router_context.profile_context_present)


if __name__ == "__main__":
    unittest.main()
