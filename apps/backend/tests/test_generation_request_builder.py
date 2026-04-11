import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import ReasoningOutput
from app.application.stylist_chat.results.decision_result import DecisionType
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode


class FakePromptBuilder:
    async def build(self, *, brief: dict[str, object]) -> dict[str, object]:
        return {
            "prompt": f"prompt::{brief.get('image_brief_en', '')}",
            "image_brief_en": brief.get("image_brief_en", ""),
            "recommendation_text": brief.get("recommendation_text", ""),
            "input_asset_id": brief.get("asset_id"),
        }


class GenerationRequestBuilderTests(unittest.IsolatedAsyncioTestCase):
    async def test_build_from_reasoning_maps_text_only_route_to_text_only_decision(self) -> None:
        builder = GenerationRequestBuilder(prompt_builder=FakePromptBuilder())
        context = ChatModeContext(active_mode=ChatMode.GENERAL_ADVICE, should_auto_generate=False)

        decision = await builder.build_from_reasoning(
            command=ChatCommand(session_id="general-1", locale="en", message="Need advice"),
            context=context,
            reasoning_output=ReasoningOutput(
                reply_text="Keep the outfit sharper.",
                image_brief_en="editorial outfit",
                route="text_only",
                provider="fake-vllm",
            ),
            asset_id=None,
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints={},
        )

        self.assertEqual(decision.decision_type, DecisionType.TEXT_ONLY)
        self.assertIsNone(decision.generation_payload)
        self.assertEqual(decision.text_reply, "Keep the outfit sharper.")

    async def test_build_from_reasoning_maps_generation_route_to_text_and_generate(self) -> None:
        builder = GenerationRequestBuilder(prompt_builder=FakePromptBuilder())
        context = ChatModeContext(active_mode=ChatMode.STYLE_EXPLORATION, should_auto_generate=True)

        decision = await builder.build_from_reasoning(
            command=ChatCommand(
                session_id="style-1",
                locale="en",
                message="Try another style",
                user_message_id=7,
            ),
            context=context,
            reasoning_output=ReasoningOutput(
                reply_text="Try a softer prep direction.",
                image_brief_en="soft prep editorial flat lay",
                route="text_and_generation",
                provider="fake-vllm",
            ),
            asset_id=42,
            must_generate=True,
            style_seed={"title": "Soft Prep", "descriptor": "relaxed collegiate layering"},
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints={},
        )

        self.assertEqual(decision.decision_type, DecisionType.TEXT_AND_GENERATE)
        assert decision.generation_payload is not None
        self.assertEqual(decision.generation_payload.prompt, "prompt::soft prep editorial flat lay")
        self.assertEqual(decision.generation_payload.input_asset_id, 42)
        self.assertEqual(decision.generation_payload.generation_intent.mode, ChatMode.STYLE_EXPLORATION)

    async def test_build_schedule_request_maps_decision_to_scheduler_payload(self) -> None:
        builder = GenerationRequestBuilder(prompt_builder=FakePromptBuilder())
        context = ChatModeContext(active_mode=ChatMode.GARMENT_MATCHING, should_auto_generate=True)
        decision = await builder.build_from_reasoning(
            command=ChatCommand(
                session_id="garment-1",
                locale="en",
                message="Indigo denim shirt",
                user_message_id=12,
                command_id="cmd-12",
            ),
            context=context,
            reasoning_output=ReasoningOutput(
                reply_text="I built a clean outfit around the shirt.",
                image_brief_en="indigo denim shirt outfit flat lay",
                route="text_and_generation",
                provider="fake-vllm",
            ),
            asset_id=99,
            must_generate=True,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints={},
        )

        request = builder.build_schedule_request(
            command=ChatCommand(
                session_id="garment-1",
                locale="en",
                message="Indigo denim shirt",
                user_message_id=12,
                command_id="cmd-12",
            ),
            context=context,
            decision=decision,
        )

        assert request is not None
        self.assertEqual(request.prompt, "prompt::indigo denim shirt outfit flat lay")
        self.assertEqual(request.input_asset_id, 99)
        self.assertEqual(request.idempotency_key, "garment-1:garment_matching:cmd:cmd-12")

    async def test_build_from_reasoning_passes_structured_garment_brief_to_prompt_builder(self) -> None:
        builder = GenerationRequestBuilder(prompt_builder=FakePromptBuilder())
        context = ChatModeContext(active_mode=ChatMode.GARMENT_MATCHING, should_auto_generate=True)

        decision = await builder.build_from_reasoning(
            command=ChatCommand(
                session_id="garment-brief-1",
                locale="en",
                message="black leather jacket",
                user_message_id=21,
            ),
            context=context,
            reasoning_output=ReasoningOutput(
                reply_text="I built a confident outfit around the jacket.",
                image_brief_en="black leather jacket outfit flat lay",
                route="text_and_generation",
                provider="fake-vllm",
            ),
            asset_id=None,
            must_generate=True,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints={},
            structured_outfit_brief={
                "brief_type": "garment_matching",
                "anchor_summary": "black leather jacket",
                "styling_goal": "Build a clean outfit around the jacket.",
            },
        )

        self.assertEqual(decision.decision_type, DecisionType.TEXT_AND_GENERATE)
        assert decision.generation_payload is not None
        self.assertEqual(decision.generation_payload.prompt, "prompt::black leather jacket outfit flat lay")
