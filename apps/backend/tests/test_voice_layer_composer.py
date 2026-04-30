import unittest

from app.application.reasoning import DefaultVoiceLayerComposer, DefaultVoicePromptBuilder, DefaultVoiceTonePolicy
from app.domain.knowledge.entities import KnowledgeRuntimeFlags
from app.domain.reasoning import (
    FashionReasoningOutput,
    StyledAnswer,
    VoiceCompositionDraft,
    VoiceContext,
    VoiceRuntimeFlags,
)


class FakeVoiceCompositionClient:
    def __init__(self, draft: VoiceCompositionDraft) -> None:
        self.draft = draft

    async def compose(self, *, prompt, context) -> VoiceCompositionDraft:
        return self.draft


class VoiceLayerComposerTests(unittest.IsolatedAsyncioTestCase):
    async def test_composer_returns_model_shaped_answer_with_separate_cta(self) -> None:
        composer = DefaultVoiceLayerComposer(
            voice_tone_policy=DefaultVoiceTonePolicy(),
            voice_prompt_builder=DefaultVoicePromptBuilder(),
            voice_composition_client=FakeVoiceCompositionClient(
                VoiceCompositionDraft(
                    final_text="Keep the line calm and let the contrast stay in the accessories.",
                    cta_text="If it helps, I can show this as a flat lay reference.",
                    used_historical_note=True,
                    used_color_poetics=True,
                    provider_model="qwen35b:latest",
                    raw_content='{"final_text":"ok"}',
                )
            ),
            enable_model_composition=True,
        )

        answer = await composer.compose(
            FashionReasoningOutput(
                response_type="visual_offer",
                text_response="Keep the line long and the contrast quiet.",
                historical_note_candidates=["it nods to late modernist restraint"],
                color_poetic_candidates=["treat ivory as a calm field of light"],
                visual_language_points=["elongated vertical rhythm"],
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
                profile_context_present=True,
                knowledge_density="high",
                locale="ru",
            ),
        )

        self.assertIsInstance(answer, StyledAnswer)
        self.assertEqual(answer.voice_layers_used, ["stylist", "historian", "color_poetics"])
        self.assertTrue(answer.includes_historical_note)
        self.assertTrue(answer.includes_color_poetics)
        self.assertEqual(answer.brevity_level, "deep")
        self.assertEqual(answer.tone_profile, "smart_stylist_with_historian_and_color_poetics_rich_but_controlled")
        self.assertEqual(
            answer.text,
            "Keep the line calm and let the contrast stay in the accessories.",
        )
        self.assertEqual(
            answer.cta_text,
            "If it helps, I can show this as a flat lay reference.",
        )
        self.assertTrue(answer.observability["voice_llm_used"])
        self.assertFalse(answer.observability["voice_llm_fallback_used"])
        self.assertEqual(answer.observability["voice_locale"], "ru")

    async def test_composer_respects_runtime_flags_and_drops_disabled_layers(self) -> None:
        composer = DefaultVoiceLayerComposer(
            knowledge_runtime_flags=KnowledgeRuntimeFlags(
                use_historical_context=False,
                use_editorial_knowledge=False,
                use_color_poetics=False,
            )
        )

        answer = await composer.compose(
            FashionReasoningOutput(
                response_type="text",
                text_response="Hold the outfit in a cleaner vertical line.",
                historical_note_candidates=["borrowed from gallery minimalism"],
                color_poetic_candidates=["quiet pearl light"],
                visual_language_points=["clean vertical line"],
            ),
            VoiceContext(
                mode="general_advice",
                response_type="text_only",
                desired_depth="normal",
                should_be_brief=False,
                can_use_historical_layer=True,
                can_use_color_poetics=True,
                can_offer_visual_cta=False,
                profile_context_present=False,
                knowledge_density="medium",
            ),
        )

        self.assertEqual(answer.voice_layers_used, ["stylist"])
        self.assertFalse(answer.includes_historical_note)
        self.assertFalse(answer.includes_color_poetics)
        self.assertEqual(answer.text, "Hold the outfit in a cleaner vertical line.")
        self.assertIsNone(answer.cta_text)

    async def test_composer_uses_experimental_cta_copy_when_enabled(self) -> None:
        composer = DefaultVoiceLayerComposer(
            voice_runtime_flags=VoiceRuntimeFlags(
                historian_enabled=True,
                color_poetics_enabled=True,
                deep_mode_enabled=True,
                cta_experimental_copy_enabled=True,
            )
        )

        answer = await composer.compose(
            FashionReasoningOutput(
                response_type="visual_offer",
                text_response="Keep the silhouette long and quiet.",
                can_offer_visualization=True,
                suggested_cta="I can show this as a flat lay reference.",
            ),
            VoiceContext(
                mode="style_exploration",
                response_type="text_with_visual_offer",
                desired_depth="deep",
                should_be_brief=False,
                can_use_historical_layer=False,
                can_use_color_poetics=False,
                can_offer_visual_cta=True,
                profile_context_present=False,
                knowledge_density="medium",
            ),
        )

        assert answer.cta_text is not None
        self.assertIn("silhouette, palette, and spacing", answer.cta_text)
        self.assertIn("I can show this as a flat lay reference", answer.cta_text)
        self.assertNotIn(answer.cta_text, answer.text)


if __name__ == "__main__":
    unittest.main()
