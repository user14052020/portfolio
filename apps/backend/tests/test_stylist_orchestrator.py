import unittest
from types import SimpleNamespace

from app.domain.chat_context import ChatModeContext, StyleDirectionContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.decision_result import DecisionType
from app.services.chat_mode_resolver import ModeResolution, chat_mode_resolver
from app.services.stylist_orchestrator import StylistChatOrchestrator


class FakeVLLMClient:
    def __init__(self) -> None:
        self.next_reply_text = "Mock stylist reply"
        self.next_route = "text_only"
        self.next_image_brief = "cohesive editorial flat lay outfit"
        self.next_occasion_result = SimpleNamespace(
            event_type=None,
            venue=None,
            dress_code=None,
            time_of_day=None,
            season_or_weather=None,
            desired_impression=None,
        )

    async def generate_stylist_response(self, **_: object):
        return SimpleNamespace(
            reply_text=self.next_reply_text,
            image_brief_en=self.next_image_brief,
            route=self.next_route,
            model="fake-vllm",
        )

    async def extract_occasion_slots(self, **_: object):
        return self.next_occasion_result


class TestStylistOrchestrator(StylistChatOrchestrator):
    def __init__(self) -> None:
        super().__init__()
        self.vllm_client = FakeVLLMClient()
        self._styles = [
            StyleDirectionContext(
                style_id="artful-minimalism",
                style_name="Artful Minimalism",
                silhouette="clean and elongated",
                hero_garments=["structured coat"],
                styling_mood="quiet and precise",
            ),
            StyleDirectionContext(
                style_id="soft-retro-prep",
                style_name="Soft Retro Prep",
                silhouette="relaxed collegiate layering",
                hero_garments=["oxford shirt"],
                styling_mood="polished but warm",
            ),
        ]
        self._style_index = 0

    async def _pick_style_direction(self, **_: object):
        style = self._styles[self._style_index % len(self._styles)]
        self._style_index += 1
        return style, None

    async def _record_style_exposure(self, *args: object, **kwargs: object) -> None:
        return None


class StylistOrchestratorScenarioTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.orchestrator = TestStylistOrchestrator()

    async def test_general_advice_flow_returns_text_only(self) -> None:
        context = ChatModeContext()
        resolution = ModeResolution(
            active_mode=ChatMode.GENERAL_ADVICE,
            started_new_mode=True,
            continue_existing_flow=False,
        )

        next_context, decision = await self.orchestrator.plan_turn(
            session=None,
            session_id="test-general",
            locale="en",
            context=context,
            resolution=resolution,
            user_message="How can I make a white shirt look more modern?",
            user_message_id=1,
            asset=None,
            recent_messages=[],
            profile_context={},
        )

        self.assertEqual(decision.decision_type, DecisionType.TEXT_ONLY)
        self.assertEqual(next_context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(next_context.flow_state, FlowState.COMPLETED)

    async def test_general_advice_follow_up_without_mode_change_stays_in_same_mode(self) -> None:
        context = ChatModeContext()
        start_resolution = ModeResolution(
            active_mode=ChatMode.GENERAL_ADVICE,
            started_new_mode=True,
            continue_existing_flow=False,
        )

        first_context, first_decision = await self.orchestrator.plan_turn(
            session=None,
            session_id="test-general-follow-up",
            locale="en",
            context=context,
            resolution=start_resolution,
            user_message="How can I make a navy blazer feel less formal?",
            user_message_id=1,
            asset=None,
            recent_messages=[],
            profile_context={},
        )

        follow_up_resolution = chat_mode_resolver.resolve(
            context=first_context,
            requested_intent=None,
            command_name=None,
            command_step=None,
            metadata=None,
        )
        second_context, second_decision = await self.orchestrator.plan_turn(
            session=None,
            session_id="test-general-follow-up",
            locale="en",
            context=first_context,
            resolution=follow_up_resolution,
            user_message="And what shoes would you add?",
            user_message_id=2,
            asset=None,
            recent_messages=[],
            profile_context={},
        )

        self.assertEqual(first_decision.decision_type, DecisionType.TEXT_ONLY)
        self.assertEqual(second_decision.decision_type, DecisionType.TEXT_ONLY)
        self.assertEqual(follow_up_resolution.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertTrue(follow_up_resolution.continue_existing_flow)
        self.assertEqual(second_context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(second_context.flow_state, FlowState.COMPLETED)

    async def test_explicit_transition_from_general_advice_to_command_mode(self) -> None:
        general_context = ChatModeContext(
            active_mode=ChatMode.GENERAL_ADVICE,
            flow_state=FlowState.COMPLETED,
        )
        resolution = chat_mode_resolver.resolve(
            context=general_context,
            requested_intent=ChatMode.GARMENT_MATCHING,
            command_name="garment_matching",
            command_step="entry",
            metadata={"source": "quick_action"},
        )

        next_context, decision = await self.orchestrator.plan_turn(
            session=None,
            session_id="test-general-to-command",
            locale="ru",
            context=general_context,
            resolution=resolution,
            user_message="Хочу подобрать образ к конкретной вещи",
            user_message_id=1,
            asset=None,
            recent_messages=[],
            profile_context={},
        )

        self.assertEqual(resolution.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertTrue(resolution.started_new_mode)
        self.assertEqual(decision.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(next_context.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertIsNotNone(next_context.command_context)
        self.assertEqual(next_context.command_context.command_name, "garment_matching")
        self.assertEqual(next_context.command_context.command_step, "entry")

    async def test_garment_matching_clarifies_then_moves_to_generation(self) -> None:
        context = ChatModeContext()
        start_resolution = ModeResolution(
            active_mode=ChatMode.GARMENT_MATCHING,
            started_new_mode=True,
            continue_existing_flow=False,
            requested_intent=ChatMode.GARMENT_MATCHING,
        )

        clarifying_context, first_decision = await self.orchestrator.plan_turn(
            session=None,
            session_id="test-garment",
            locale="ru",
            context=context,
            resolution=start_resolution,
            user_message="Помоги подобрать образ к вещи",
            user_message_id=1,
            asset=None,
            recent_messages=[],
            profile_context={},
        )

        self.assertEqual(first_decision.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(clarifying_context.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertEqual(clarifying_context.flow_state, FlowState.AWAITING_CLARIFICATION)

        follow_up_resolution = ModeResolution(
            active_mode=ChatMode.GARMENT_MATCHING,
            started_new_mode=False,
            continue_existing_flow=True,
            requested_intent=ChatMode.GARMENT_MATCHING,
        )
        ready_context, second_decision = await self.orchestrator.plan_turn(
            session=None,
            session_id="test-garment",
            locale="ru",
            context=clarifying_context,
            resolution=follow_up_resolution,
            user_message="Темно-синяя джинсовая рубашка прямого кроя",
            user_message_id=2,
            asset=None,
            recent_messages=[],
            profile_context={"gender": "male"},
        )

        self.assertEqual(second_decision.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertIsNotNone(ready_context.anchor_garment)
        self.assertTrue(ready_context.anchor_garment.is_sufficient_for_generation)
        self.assertEqual(ready_context.flow_state, FlowState.READY_FOR_GENERATION)

    async def test_style_exploration_keeps_history_and_avoids_general_chat(self) -> None:
        context = ChatModeContext()
        resolution = ModeResolution(
            active_mode=ChatMode.STYLE_EXPLORATION,
            started_new_mode=True,
            continue_existing_flow=False,
            requested_intent=ChatMode.STYLE_EXPLORATION,
        )

        first_context, first_decision = await self.orchestrator.plan_turn(
            session=None,
            session_id="test-style",
            locale="en",
            context=context,
            resolution=resolution,
            user_message="Try another style",
            user_message_id=1,
            asset=None,
            recent_messages=[],
            profile_context={},
        )

        second_context, second_decision = await self.orchestrator.plan_turn(
            session=None,
            session_id="test-style",
            locale="en",
            context=first_context,
            resolution=resolution,
            user_message="Try another style",
            user_message_id=2,
            asset=None,
            recent_messages=[],
            profile_context={},
        )

        self.assertEqual(first_decision.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(second_decision.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(first_context.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertEqual(second_context.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertGreaterEqual(len(second_context.style_history), 2)
        self.assertNotEqual(
            second_context.style_history[-1].style_id,
            second_context.style_history[-2].style_id,
        )

    async def test_occasion_outfit_collects_slots_and_generates(self) -> None:
        context = ChatModeContext()
        resolution = ModeResolution(
            active_mode=ChatMode.OCCASION_OUTFIT,
            started_new_mode=True,
            continue_existing_flow=False,
            requested_intent=ChatMode.OCCASION_OUTFIT,
        )

        self.orchestrator.vllm_client.next_occasion_result = SimpleNamespace(
            event_type=None,
            venue=None,
            dress_code=None,
            time_of_day=None,
            season_or_weather=None,
            desired_impression=None,
        )
        clarifying_context, first_decision = await self.orchestrator.plan_turn(
            session=None,
            session_id="test-occasion",
            locale="ru",
            context=context,
            resolution=resolution,
            user_message="Мне нужен образ на событие",
            user_message_id=1,
            asset=None,
            recent_messages=[],
            profile_context={},
        )

        self.assertEqual(first_decision.decision_type, DecisionType.CLARIFICATION_REQUIRED)
        self.assertEqual(clarifying_context.flow_state, FlowState.AWAITING_CLARIFICATION)

        self.orchestrator.vllm_client.next_occasion_result = SimpleNamespace(
            event_type="wedding",
            venue=None,
            dress_code="cocktail",
            time_of_day="evening",
            season_or_weather="spring",
            desired_impression=None,
        )
        ready_context, second_decision = await self.orchestrator.plan_turn(
            session=None,
            session_id="test-occasion",
            locale="ru",
            context=clarifying_context,
            resolution=ModeResolution(
                active_mode=ChatMode.OCCASION_OUTFIT,
                started_new_mode=False,
                continue_existing_flow=True,
                requested_intent=ChatMode.OCCASION_OUTFIT,
            ),
            user_message="На свадьбу вечером весной, dress code cocktail",
            user_message_id=2,
            asset=None,
            recent_messages=[],
            profile_context={},
        )

        self.assertEqual(second_decision.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertIsNotNone(ready_context.occasion_context)
        self.assertTrue(ready_context.occasion_context.is_sufficient_for_generation)
        self.assertEqual(ready_context.occasion_context.event_type, "wedding")
        self.assertEqual(ready_context.occasion_context.time_of_day, "evening")
        self.assertEqual(ready_context.occasion_context.season, "spring")
        self.assertEqual(ready_context.occasion_context.dress_code, "cocktail")
        self.assertEqual(ready_context.flow_state, FlowState.READY_FOR_GENERATION)
