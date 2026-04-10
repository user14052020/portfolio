import unittest

from app.domain.chat_context import AnchorGarment, ChatModeContext, OccasionContext, StyleDirectionContext
from app.domain.chat_modes import ChatMode, ClarificationKind, FlowState
from app.domain.state_machine.garment_matching_machine import GarmentMatchingStateMachine
from app.domain.state_machine.general_advice_machine import GeneralAdviceStateMachine
from app.domain.state_machine.occasion_outfit_machine import OccasionOutfitStateMachine
from app.domain.state_machine.style_exploration_machine import StyleExplorationStateMachine


class StateMachineTests(unittest.TestCase):
    def test_garment_matching_enter_sets_expected_initial_state(self) -> None:
        context = ChatModeContext()

        GarmentMatchingStateMachine.enter(context, prompt_text="Describe the garment")

        self.assertEqual(context.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertEqual(context.flow_state, FlowState.AWAITING_ANCHOR_GARMENT)
        self.assertEqual(context.pending_clarification, "Describe the garment")
        self.assertEqual(context.clarification_kind, ClarificationKind.ANCHOR_GARMENT_DESCRIPTION)
        self.assertTrue(context.should_auto_generate)

    def test_garment_matching_consume_incomplete_anchor_requests_clarification(self) -> None:
        context = ChatModeContext()
        GarmentMatchingStateMachine.enter(context, prompt_text="Describe the garment")

        GarmentMatchingStateMachine.consume_anchor_garment(
            context,
            anchor_garment=AnchorGarment(raw_user_text="shirt", garment_type="shirt"),
            clarification_text="Need color or material",
        )

        self.assertEqual(context.flow_state, FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION)
        self.assertEqual(context.pending_clarification, "Need color or material")
        self.assertEqual(context.clarification_kind, ClarificationKind.ANCHOR_GARMENT_MISSING_ATTRIBUTES)
        self.assertEqual(context.clarification_attempts, 1)

    def test_garment_matching_consume_sufficient_anchor_moves_ready(self) -> None:
        context = ChatModeContext()
        GarmentMatchingStateMachine.enter(context, prompt_text="Describe the garment")

        GarmentMatchingStateMachine.consume_anchor_garment(
            context,
            anchor_garment=AnchorGarment(
                raw_user_text="indigo denim shirt",
                garment_type="shirt",
                color_primary="indigo",
                material="denim",
                is_sufficient_for_generation=True,
            ),
        )

        self.assertEqual(context.flow_state, FlowState.READY_FOR_DECISION)
        self.assertIsNone(context.pending_clarification)
        self.assertIsNone(context.clarification_kind)

    def test_occasion_outfit_enter_sets_expected_initial_state(self) -> None:
        context = ChatModeContext()

        OccasionOutfitStateMachine.enter(context, prompt_text="Tell me about the event")

        self.assertEqual(context.active_mode, ChatMode.OCCASION_OUTFIT)
        self.assertEqual(context.flow_state, FlowState.AWAITING_OCCASION_DETAILS)
        self.assertEqual(context.pending_clarification, "Tell me about the event")
        self.assertEqual(context.clarification_kind, ClarificationKind.OCCASION_MISSING_MULTIPLE_SLOTS)
        self.assertTrue(context.should_auto_generate)

    def test_occasion_outfit_consume_incomplete_context_requests_clarification(self) -> None:
        context = ChatModeContext()
        OccasionOutfitStateMachine.enter(context, prompt_text="Tell me about the event")

        OccasionOutfitStateMachine.consume_occasion_context(
            context,
            occasion_context=OccasionContext(event_type="wedding"),
            clarification_kind=ClarificationKind.OCCASION_TIME_OF_DAY,
            clarification_text="Need time of day",
        )

        self.assertEqual(context.flow_state, FlowState.AWAITING_OCCASION_CLARIFICATION)
        self.assertEqual(context.pending_clarification, "Need time of day")
        self.assertEqual(context.clarification_attempts, 1)

    def test_occasion_outfit_consume_complete_context_moves_ready(self) -> None:
        context = ChatModeContext()
        OccasionOutfitStateMachine.enter(context, prompt_text="Tell me about the event")

        OccasionOutfitStateMachine.consume_occasion_context(
            context,
            occasion_context=OccasionContext(
                event_type="wedding",
                time_of_day="evening",
                season="spring",
                dress_code="cocktail",
                is_sufficient_for_generation=True,
            ),
            clarification_kind=None,
            clarification_text=None,
        )

        self.assertEqual(context.flow_state, FlowState.READY_FOR_DECISION)
        self.assertIsNone(context.pending_clarification)
        self.assertIsNone(context.clarification_kind)

    def test_general_advice_cycle_reaches_completed(self) -> None:
        context = ChatModeContext()

        GeneralAdviceStateMachine.enter(context)
        GeneralAdviceStateMachine.accept_user_message(context)
        GeneralAdviceStateMachine.complete(context)

        self.assertEqual(context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(context.flow_state, FlowState.COMPLETED)
        self.assertFalse(context.should_auto_generate)

    def test_style_exploration_select_style_updates_history(self) -> None:
        context = ChatModeContext()
        style = StyleDirectionContext(style_id="soft-retro-prep", style_name="Soft Retro Prep")

        StyleExplorationStateMachine.enter(context)
        StyleExplorationStateMachine.select_style(context, style=style)
        StyleExplorationStateMachine.mark_ready_for_generation(context)

        self.assertEqual(context.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertEqual(context.current_style_id, "soft-retro-prep")
        self.assertEqual(context.current_style_name, "Soft Retro Prep")
        self.assertEqual(context.flow_state, FlowState.READY_FOR_GENERATION)
        self.assertEqual(len(context.style_history), 1)
