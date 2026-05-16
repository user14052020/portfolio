import unittest

from app.application.reasoning import DefaultReasoningOutputMapper
from app.domain.reasoning import FashionReasoningOutput, VoiceContext


class VoiceLayerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.mapper = DefaultReasoningOutputMapper()

    async def test_light_general_advice_stays_stylist_only(self) -> None:
        payload = await self.mapper.to_presentation(
            FashionReasoningOutput(
                response_type="text",
                text_response="Keep the proportions easy and the palette quiet.",
                style_logic_points=["keep the proportions easy"],
                visual_language_points=["quiet palette"],
            ),
            voice_context=self._voice_context(
                mode="general_advice",
                response_type="text_only",
                desired_depth="light",
                should_be_brief=True,
                knowledge_density="low",
            ),
        )

        self.assertEqual(payload.voice.voice_layers_used, ["stylist"])
        self.assertFalse(payload.voice.includes_historical_note)
        self.assertFalse(payload.voice.includes_color_poetics)
        self.assertEqual(payload.voice.brevity_level, "light")
        self.assertNotIn("Historically,", payload.voice.draft_text)
        self.assertNotIn("Visually,", payload.voice.draft_text)
        self.assertLessEqual(len(payload.voice.draft_text.split()), 12)

    async def test_occasion_outfit_normal_depth_stays_balanced_without_extra_layers(self) -> None:
        payload = await self.mapper.to_presentation(
            FashionReasoningOutput(
                response_type="text",
                text_response="Keep the shape polished, then let the shoes carry the formality.",
                style_logic_points=["keep the shape polished"],
                visual_language_points=["let the shoes carry the formality"],
                historical_note_candidates=["rooted in postwar cocktail dressing"],
                color_poetic_candidates=["quiet satin light"],
            ),
            voice_context=self._voice_context(
                mode="occasion_outfit",
                response_type="text_with_brief",
                desired_depth="normal",
                should_be_brief=False,
                knowledge_density="medium",
            ),
        )

        self.assertEqual(payload.voice.voice_layers_used, ["stylist"])
        self.assertFalse(payload.voice.includes_historical_note)
        self.assertFalse(payload.voice.includes_color_poetics)
        self.assertEqual(payload.voice.brevity_level, "normal")
        self.assertNotIn("Historically,", payload.voice.draft_text)
        self.assertNotIn("Visually,", payload.voice.draft_text)

    async def test_deep_style_exploration_activates_historian_and_color_layers(self) -> None:
        payload = await self.mapper.to_presentation(
            FashionReasoningOutput(
                response_type="visual_offer",
                text_response="Keep the line long and quiet, then let the shine sit in the accessories.",
                style_logic_points=["keep the line long"],
                visual_language_points=["quiet contrast and elongated line"],
                historical_note_candidates=["it nods to late modernist restraint"],
                color_poetic_candidates=["treat ivory as a calm field of light"],
                can_offer_visualization=True,
                suggested_cta="I can show this as a flat lay reference.",
            ),
            voice_context=self._voice_context(
                mode="style_exploration",
                response_type="text_with_visual_offer",
                desired_depth="deep",
                should_be_brief=False,
                knowledge_density="high",
            ),
        )

        self.assertEqual(payload.voice.voice_layers_used, ["stylist", "historian", "color_poetics"])
        self.assertTrue(payload.voice.includes_historical_note)
        self.assertTrue(payload.voice.includes_color_poetics)
        self.assertEqual(payload.voice.brevity_level, "deep")
        self.assertIn("Historically, it nods to late modernist restraint.", payload.voice.draft_text)
        self.assertIn("Visually, treat ivory as a calm field of light.", payload.voice.draft_text)
        self.assertEqual(
            payload.voice.cta_text,
            "If it helps, I can show this as a flat lay reference so you can see the logic visually.",
        )
        self.assertNotIn("If it helps, I can show this as a flat lay reference", payload.voice.draft_text)

    async def test_clarification_only_stays_direct_and_without_cta(self) -> None:
        payload = await self.mapper.to_presentation(
            FashionReasoningOutput(
                response_type="clarification",
                text_response="Do you want a softer fit or a more structured silhouette?",
                clarification_question="Do you want a softer fit or a more structured silhouette?",
            ),
            voice_context=self._voice_context(
                mode="clarification_only",
                response_type="clarification",
                desired_depth="light",
                should_be_brief=True,
                knowledge_density="low",
                can_offer_visual_cta=False,
            ),
        )

        self.assertEqual(payload.voice.voice_layers_used, ["stylist"])
        self.assertEqual(
            payload.voice.draft_text,
            "Do you want a softer fit or a more structured silhouette?",
        )
        self.assertIsNone(payload.voice.cta_text)
        self.assertFalse(payload.voice.includes_historical_note)
        self.assertFalse(payload.voice.includes_color_poetics)

    async def test_strong_visual_language_answer_uses_color_poetics_without_history(self) -> None:
        payload = await self.mapper.to_presentation(
            FashionReasoningOutput(
                response_type="text",
                text_response="Keep the outfit spare, then let the gloss arrive in one concentrated accent.",
                style_logic_points=["keep the outfit spare"],
                visual_language_points=["let the gloss arrive in one concentrated accent"],
                color_poetic_candidates=["treat pearl as a focused line of light"],
            ),
            voice_context=self._voice_context(
                mode="style_exploration",
                response_type="text_only",
                desired_depth="deep",
                should_be_brief=False,
                can_use_historical_layer=False,
                can_use_color_poetics=True,
                knowledge_density="high",
            ),
        )

        self.assertEqual(payload.voice.voice_layers_used, ["stylist", "color_poetics"])
        self.assertFalse(payload.voice.includes_historical_note)
        self.assertTrue(payload.voice.includes_color_poetics)
        self.assertIn("Visually, treat pearl as a focused line of light.", payload.voice.draft_text)
        self.assertNotIn("Historically,", payload.voice.draft_text)

    async def test_no_history_answer_even_if_history_candidates_available_when_context_disallows_it(self) -> None:
        payload = await self.mapper.to_presentation(
            FashionReasoningOutput(
                response_type="text",
                text_response="Hold the outfit in a cleaner vertical line.",
                style_logic_points=["hold the outfit in a cleaner vertical line"],
                historical_note_candidates=["it echoes late gallery minimalism"],
                color_poetic_candidates=["quiet pearl light"],
            ),
            voice_context=self._voice_context(
                mode="general_advice",
                response_type="text_only",
                desired_depth="normal",
                should_be_brief=False,
                can_use_historical_layer=False,
                can_use_color_poetics=False,
                knowledge_density="medium",
            ),
        )

        self.assertEqual(payload.voice.voice_layers_used, ["stylist"])
        self.assertFalse(payload.voice.includes_historical_note)
        self.assertFalse(payload.voice.includes_color_poetics)
        self.assertEqual(payload.voice.draft_text, "Hold the outfit in a cleaner vertical line.")

    def _voice_context(
        self,
        *,
        mode: str,
        response_type: str,
        desired_depth: str,
        should_be_brief: bool,
        knowledge_density: str,
        can_use_historical_layer: bool = True,
        can_use_color_poetics: bool = True,
        can_offer_visual_cta: bool = True,
    ) -> VoiceContext:
        return VoiceContext(
            mode=mode,
            response_type=response_type,
            desired_depth=desired_depth,
            should_be_brief=should_be_brief,
            can_use_historical_layer=can_use_historical_layer,
            can_use_color_poetics=can_use_color_poetics,
            can_offer_visual_cta=can_offer_visual_cta,
            profile_context_present=False,
            knowledge_density=knowledge_density,
        )


class VoiceLayerProductToneTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.mapper = DefaultReasoningOutputMapper()

    async def test_bot_feels_intelligent_not_theatrical(self) -> None:
        payload = await self.mapper.to_presentation(
            FashionReasoningOutput(
                response_type="visual_offer",
                text_response="Keep the silhouette strict, then let the contrast sit in one precise accessory.",
                style_logic_points=["keep the silhouette strict"],
                visual_language_points=["precise contrast"],
                historical_note_candidates=["it echoes late modernist restraint"],
                color_poetic_candidates=["treat ivory as a steady field of light"],
                can_offer_visualization=True,
                suggested_cta="I can show this as a flat lay reference.",
            ),
            voice_context=VoiceContext(
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
        )

        self.assertTrue(payload.voice.tone_profile.startswith("smart_stylist"))
        self.assertIn("Keep the silhouette strict", payload.voice.draft_text)
        self.assertNotIn("!", payload.voice.draft_text)
        self.assertLessEqual(len(payload.voice.draft_text.split()), 50)

    async def test_text_remains_useful_and_cta_feels_natural(self) -> None:
        payload = await self.mapper.to_presentation(
            FashionReasoningOutput(
                response_type="visual_offer",
                text_response="Keep the jacket line clean and let the shoe do the formal work.",
                style_logic_points=["keep the jacket line clean"],
                can_offer_visualization=True,
                suggested_cta="I can show this as a flat lay reference.",
            ),
            voice_context=VoiceContext(
                mode="occasion_outfit",
                response_type="text_with_visual_offer",
                desired_depth="normal",
                should_be_brief=False,
                can_use_historical_layer=False,
                can_use_color_poetics=False,
                can_offer_visual_cta=True,
                profile_context_present=True,
                knowledge_density="medium",
            ),
        )

        assert payload.voice.cta_text is not None
        self.assertIn("Keep the jacket line clean", payload.voice.draft_text)
        self.assertTrue(
            payload.voice.cta_text.startswith("If you want,")
            or payload.voice.cta_text.startswith("If it helps,")
        )
        self.assertNotIn(payload.voice.cta_text, payload.voice.draft_text)
        self.assertLessEqual(len(payload.voice.draft_text.split()), 28)

    async def test_persona_remains_consistent_across_modes(self) -> None:
        general_payload = await self.mapper.to_presentation(
            FashionReasoningOutput(
                response_type="text",
                text_response="Keep the palette quiet and the shape easy.",
            ),
            voice_context=VoiceContext(
                mode="general_advice",
                response_type="text_only",
                desired_depth="light",
                should_be_brief=True,
                can_use_historical_layer=False,
                can_use_color_poetics=False,
                can_offer_visual_cta=False,
                profile_context_present=False,
                knowledge_density="low",
            ),
        )
        exploration_payload = await self.mapper.to_presentation(
            FashionReasoningOutput(
                response_type="text",
                text_response="Keep the line long and quiet.",
                color_poetic_candidates=["treat ivory as a calm field of light"],
            ),
            voice_context=VoiceContext(
                mode="style_exploration",
                response_type="text_only",
                desired_depth="deep",
                should_be_brief=False,
                can_use_historical_layer=False,
                can_use_color_poetics=True,
                can_offer_visual_cta=False,
                profile_context_present=False,
                knowledge_density="high",
            ),
        )

        self.assertTrue(general_payload.voice.tone_profile.startswith("smart_stylist"))
        self.assertTrue(exploration_payload.voice.tone_profile.startswith("smart_stylist"))
        self.assertIn("Keep the palette quiet", general_payload.voice.draft_text)
        self.assertIn("Keep the line long", exploration_payload.voice.draft_text)


if __name__ == "__main__":
    unittest.main()
