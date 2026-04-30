import unittest

from app.application.reasoning import DefaultVoicePromptBuilder
from app.domain.reasoning import (
    FashionReasoningOutput,
    VoiceContext,
    VoicePrompt,
    VoiceRuntimeFlags,
    VoiceToneDecision,
)


class VoicePromptBuilderTests(unittest.IsolatedAsyncioTestCase):
    async def test_builder_shapes_deep_style_exploration_prompt_with_requested_layers(self) -> None:
        builder = DefaultVoicePromptBuilder()

        prompt = await builder.build(
            FashionReasoningOutput(
                response_type="visual_offer",
                text_response="Keep the silhouette long and quiet, then let the contrast sit in the accessories.",
                style_logic_points=["keep the silhouette long"],
                visual_language_points=["quiet contrast and elongated line"],
                historical_note_candidates=["echoes late modernist restraint"],
                styling_rule_candidates=["anchor the look with one dark vertical"],
                editorial_context_candidates=["editorial restraint over costume drama"],
                color_poetic_candidates=["treat ivory as a calm field of light"],
                composition_theory_candidates=["use diagonal spacing to keep the layout breathing"],
                can_offer_visualization=True,
                suggested_cta="If helpful, I can show this as a flat lay reference.",
            ),
            VoiceContext(
                mode="style_exploration",
                response_type="text_with_visual_offer",
                desired_depth="deep",
                should_be_brief=False,
                can_use_historical_layer=True,
                can_use_color_poetics=True,
                can_offer_visual_cta=True,
                profile_context_present=True,
                knowledge_density="high",
            ),
            VoiceToneDecision(
                base_tone="smart_stylist",
                use_historian_layer=True,
                use_color_poetics_layer=True,
                brevity_level="deep",
                expressive_density="rich_but_controlled",
                cta_style="editorial_soft",
            ),
        )

        self.assertIsInstance(prompt, VoicePrompt)
        self.assertEqual(prompt.layers_requested, ["stylist", "historian", "color_poetics"])
        self.assertEqual(prompt.brevity_level, "deep")
        self.assertEqual(prompt.cta_style, "editorial_soft")
        self.assertIn("Do not invent new fashion logic.", prompt.system_prompt)
        self.assertIn("Return strict JSON only with keys:", prompt.system_prompt)
        self.assertIn("Reply in locale: en.", prompt.system_prompt)
        self.assertIn("The reasoning is already profile-aware.", prompt.system_prompt)
        self.assertIn("Historical context may be used only", prompt.system_prompt)
        self.assertIn("Color and form poetics may be used only", prompt.system_prompt)
        self.assertIn("Style logic points:", prompt.user_prompt)
        self.assertIn("Historical note candidates:", prompt.user_prompt)
        self.assertIn("Color poetic candidates:", prompt.user_prompt)
        self.assertIn("CTA guidance:", prompt.user_prompt)
        self.assertEqual(
            prompt.observability["voice_prompt_layers_requested"],
            ["stylist", "historian", "color_poetics"],
        )
        self.assertEqual(prompt.observability["voice_prompt_locale"], "en")

    async def test_builder_keeps_clarification_prompt_direct_and_without_extra_layers(self) -> None:
        builder = DefaultVoicePromptBuilder()

        prompt = await builder.build(
            FashionReasoningOutput(
                response_type="clarification",
                text_response="Do you want a softer fit or a more structured silhouette?",
                clarification_question="Do you want a softer fit or a more structured silhouette?",
                can_offer_visualization=False,
            ),
            VoiceContext(
                mode="clarification_only",
                response_type="clarification",
                desired_depth="light",
                should_be_brief=True,
                can_use_historical_layer=True,
                can_use_color_poetics=True,
                can_offer_visual_cta=False,
                profile_context_present=False,
                knowledge_density="low",
            ),
            VoiceToneDecision(
                base_tone="smart_stylist",
                use_historian_layer=False,
                use_color_poetics_layer=False,
                brevity_level="light",
                expressive_density="minimal",
                cta_style=None,
            ),
        )

        self.assertEqual(prompt.layers_requested, ["stylist"])
        self.assertEqual(prompt.brevity_level, "light")
        self.assertIsNone(prompt.cta_style)
        self.assertIn("Keep the response extremely direct and practical.", prompt.system_prompt)
        self.assertIn("Reply in locale: en.", prompt.system_prompt)
        self.assertNotIn("Historical note candidates:", prompt.user_prompt)
        self.assertNotIn("Color poetic candidates:", prompt.user_prompt)
        self.assertNotIn("CTA guidance:", prompt.user_prompt)

    async def test_builder_respects_disabled_voice_layers_and_deep_mode_flags(self) -> None:
        builder = DefaultVoicePromptBuilder(
            voice_runtime_flags=VoiceRuntimeFlags(
                historian_enabled=False,
                color_poetics_enabled=False,
                deep_mode_enabled=False,
                cta_experimental_copy_enabled=False,
            )
        )

        prompt = await builder.build(
            FashionReasoningOutput(
                response_type="visual_offer",
                text_response="Keep the line quiet.",
                historical_note_candidates=["late modernist restraint"],
                color_poetic_candidates=["quiet ivory light"],
                visual_language_points=["clean vertical rhythm"],
                can_offer_visualization=True,
                suggested_cta="I can show this as a flat lay reference.",
            ),
            VoiceContext(
                mode="style_exploration",
                response_type="text_with_visual_offer",
                desired_depth="deep",
                should_be_brief=False,
                can_use_historical_layer=True,
                can_use_color_poetics=True,
                can_offer_visual_cta=True,
                profile_context_present=False,
                knowledge_density="high",
            ),
            VoiceToneDecision(
                base_tone="smart_stylist",
                use_historian_layer=True,
                use_color_poetics_layer=True,
                brevity_level="deep",
                expressive_density="rich_but_controlled",
                cta_style="editorial_soft",
            ),
        )

        self.assertEqual(prompt.layers_requested, ["stylist"])
        self.assertEqual(prompt.brevity_level, "normal")
        self.assertNotIn("Historical note candidates:", prompt.user_prompt)
        self.assertNotIn("Color poetic candidates:", prompt.user_prompt)


if __name__ == "__main__":
    unittest.main()
