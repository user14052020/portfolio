from app.domain.knowledge.entities import KnowledgeRuntimeFlags
from app.application.reasoning.contracts import (
    VoiceCompositionClient,
    VoiceLayerComposer,
    VoiceRuntimeSettingsProvider,
)
from app.application.reasoning.services.voice_layer_composer import DefaultVoiceLayerComposer
from app.domain.reasoning import (
    FashionReasoningOutput,
    FashionReasoningPresentationPayload,
    GenerationHandoffPayload,
    VoiceContext,
    VoiceLayerReasoningPayload,
)


class DefaultReasoningOutputMapper:
    def __init__(
        self,
        *,
        voice_layer_composer: VoiceLayerComposer | None = None,
        voice_composition_client: VoiceCompositionClient | None = None,
        voice_runtime_settings_provider: VoiceRuntimeSettingsProvider | None = None,
        enable_model_composition: bool = False,
    ) -> None:
        self._voice_layer_composer = voice_layer_composer or DefaultVoiceLayerComposer(
            voice_composition_client=voice_composition_client,
            voice_runtime_settings_provider=voice_runtime_settings_provider,
            enable_model_composition=enable_model_composition,
        )

    async def to_presentation(
        self,
        reasoning_output: FashionReasoningOutput,
        *,
        voice_context: VoiceContext | None = None,
        runtime_flags: KnowledgeRuntimeFlags | None = None,
    ) -> FashionReasoningPresentationPayload:
        effective_context = voice_context or self._fallback_voice_context(reasoning_output)
        styled_answer = await self._voice_layer_composer.compose(
            reasoning_output,
            effective_context,
            runtime_flags=runtime_flags,
        )
        voice_observability = {
            **dict(reasoning_output.observability),
            **dict(styled_answer.observability),
            "voice_layers_used": list(styled_answer.voice_layers_used),
            "voice_tone_profile": styled_answer.tone_profile,
            "voice_brevity_level": styled_answer.brevity_level,
            "voice_historical_used": styled_answer.includes_historical_note,
            "voice_color_poetics_used": styled_answer.includes_color_poetics,
            "voice_cta_present": bool(styled_answer.cta_text),
        }
        voice_payload = VoiceLayerReasoningPayload(
            response_type=reasoning_output.response_type,
            draft_text=styled_answer.text,
            tone_profile=styled_answer.tone_profile,
            voice_layers_used=list(styled_answer.voice_layers_used),
            includes_historical_note=styled_answer.includes_historical_note,
            includes_color_poetics=styled_answer.includes_color_poetics,
            cta_text=styled_answer.cta_text,
            brevity_level=styled_answer.brevity_level,
            clarification_question=reasoning_output.clarification_question,
            style_logic_points=list(reasoning_output.style_logic_points),
            visual_language_points=list(reasoning_output.visual_language_points),
            historical_note_candidates=list(reasoning_output.historical_note_candidates),
            styling_rule_candidates=list(reasoning_output.styling_rule_candidates),
            editorial_context_candidates=list(reasoning_output.editorial_context_candidates),
            color_poetic_candidates=list(reasoning_output.color_poetic_candidates),
            composition_theory_candidates=list(reasoning_output.composition_theory_candidates),
            can_offer_visualization=reasoning_output.can_offer_visualization,
            suggested_cta=reasoning_output.suggested_cta,
            observability=voice_observability,
        )
        generation_payload = GenerationHandoffPayload(
            generation_ready=reasoning_output.has_generation_handoff(),
            fashion_brief=reasoning_output.fashion_brief if reasoning_output.has_generation_handoff() else None,
            image_cta_candidates=list(reasoning_output.image_cta_candidates),
            blocked_reason=reasoning_output.generation_blocked_reason(),
            observability=dict(reasoning_output.observability),
        )
        return FashionReasoningPresentationPayload(
            voice=voice_payload,
            generation=generation_payload,
            observability={
                **dict(reasoning_output.observability),
                **dict(styled_answer.observability),
                "voice_layers_used": list(styled_answer.voice_layers_used),
                "voice_tone_profile": styled_answer.tone_profile,
                "voice_brevity_level": styled_answer.brevity_level,
            },
        )

    def _fallback_voice_context(self, reasoning_output: FashionReasoningOutput) -> VoiceContext:
        if reasoning_output.response_type == "clarification":
            return VoiceContext(
                mode="clarification_only",
                response_type="clarification",
                desired_depth="light",
                should_be_brief=True,
                can_use_historical_layer=False,
                can_use_color_poetics=False,
                can_offer_visual_cta=False,
                profile_context_present=False,
                knowledge_density="low",
            )

        knowledge_density = "high" if (
            len(reasoning_output.style_logic_points)
            + len(reasoning_output.visual_language_points)
            + len(reasoning_output.historical_note_candidates)
            + len(reasoning_output.color_poetic_candidates)
        ) >= 4 else "medium"
        desired_depth = (
            "deep"
            if reasoning_output.response_type in {"visual_offer", "generation_ready"}
            and knowledge_density == "high"
            else "normal"
        )
        response_type = {
            "text": "text_only",
            "visual_offer": "text_with_visual_offer",
            "generation_ready": "brief_ready_for_generation",
            "clarification": "clarification",
        }.get(reasoning_output.response_type, "text_only")
        return VoiceContext(
            mode="style_exploration" if response_type != "text_only" else "general_advice",
            response_type=response_type,
            desired_depth=desired_depth,
            should_be_brief=response_type == "text_only" and knowledge_density == "medium",
            can_use_historical_layer=bool(reasoning_output.historical_note_candidates),
            can_use_color_poetics=bool(
                reasoning_output.color_poetic_candidates
                or reasoning_output.composition_theory_candidates
                or reasoning_output.visual_language_points
            ),
            can_offer_visual_cta=reasoning_output.can_offer_visualization,
            profile_context_present=bool(
                reasoning_output.observability.get("profile_context_present")
                or reasoning_output.observability.get("profile_alignment_applied")
            ),
            knowledge_density=knowledge_density,
        )
