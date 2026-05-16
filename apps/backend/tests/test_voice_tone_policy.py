import unittest

from app.application.reasoning import DefaultVoiceTonePolicy
from app.domain.reasoning import VoiceContext, VoiceRuntimeFlags


class VoiceTonePolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_general_advice_light_prefers_brief_restrained_voice(self) -> None:
        policy = DefaultVoiceTonePolicy()

        decision = await policy.resolve(
            VoiceContext(
                mode="general_advice",
                response_type="text_only",
                desired_depth="light",
                should_be_brief=True,
                can_use_historical_layer=True,
                can_use_color_poetics=True,
                can_offer_visual_cta=True,
                profile_context_present=False,
                knowledge_density="low",
            )
        )

        self.assertEqual(decision.base_tone, "smart_stylist")
        self.assertFalse(decision.use_historian_layer)
        self.assertFalse(decision.use_color_poetics_layer)
        self.assertEqual(decision.brevity_level, "light")
        self.assertEqual(decision.expressive_density, "restrained")
        self.assertEqual(decision.cta_style, "neutral")

    async def test_style_exploration_deep_activates_historian_and_color_layers(self) -> None:
        policy = DefaultVoiceTonePolicy()

        decision = await policy.resolve(
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
            )
        )

        self.assertEqual(decision.base_tone, "smart_stylist")
        self.assertTrue(decision.use_historian_layer)
        self.assertTrue(decision.use_color_poetics_layer)
        self.assertEqual(decision.brevity_level, "deep")
        self.assertEqual(decision.expressive_density, "rich_but_controlled")
        self.assertEqual(decision.cta_style, "editorial_soft")

    async def test_clarification_stays_minimal_and_never_offers_cta(self) -> None:
        policy = DefaultVoiceTonePolicy()

        decision = await policy.resolve(
            VoiceContext(
                mode="clarification_only",
                response_type="clarification",
                desired_depth="normal",
                should_be_brief=False,
                can_use_historical_layer=True,
                can_use_color_poetics=True,
                can_offer_visual_cta=True,
                profile_context_present=True,
                knowledge_density="high",
            )
        )

        self.assertFalse(decision.use_historian_layer)
        self.assertFalse(decision.use_color_poetics_layer)
        self.assertEqual(decision.brevity_level, "light")
        self.assertEqual(decision.expressive_density, "minimal")
        self.assertIsNone(decision.cta_style)

    async def test_occasion_outfit_normal_keeps_balanced_voice_without_poetics(self) -> None:
        policy = DefaultVoiceTonePolicy()

        decision = await policy.resolve(
            VoiceContext(
                mode="occasion_outfit",
                response_type="text_with_brief",
                desired_depth="normal",
                should_be_brief=False,
                can_use_historical_layer=True,
                can_use_color_poetics=True,
                can_offer_visual_cta=True,
                profile_context_present=True,
                knowledge_density="medium",
            )
        )

        self.assertFalse(decision.use_historian_layer)
        self.assertFalse(decision.use_color_poetics_layer)
        self.assertEqual(decision.brevity_level, "normal")
        self.assertEqual(decision.expressive_density, "balanced")
        self.assertEqual(decision.cta_style, "soft")

    async def test_flags_can_disable_deep_mode_and_historian_layer(self) -> None:
        policy = DefaultVoiceTonePolicy(
            voice_runtime_flags=VoiceRuntimeFlags(
                historian_enabled=False,
                color_poetics_enabled=True,
                deep_mode_enabled=False,
                cta_experimental_copy_enabled=True,
            )
        )

        decision = await policy.resolve(
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
            )
        )

        self.assertFalse(decision.use_historian_layer)
        self.assertFalse(decision.use_color_poetics_layer)
        self.assertEqual(decision.brevity_level, "normal")
        self.assertEqual(decision.cta_style, "soft")


if __name__ == "__main__":
    unittest.main()
