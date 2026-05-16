from app.domain.reasoning import (
    FashionReasoningOutput,
    FashionReasoningPresentationPayload,
    GenerationHandoffPayload,
    VoiceLayerReasoningPayload,
)


class DefaultReasoningOutputMapper:
    def to_presentation(self, reasoning_output: FashionReasoningOutput) -> FashionReasoningPresentationPayload:
        voice_payload = VoiceLayerReasoningPayload(
            response_type=reasoning_output.response_type,
            draft_text=reasoning_output.text_response,
            clarification_question=reasoning_output.clarification_question,
            style_logic_points=list(reasoning_output.style_logic_points),
            visual_language_points=list(reasoning_output.visual_language_points),
            historical_note_candidates=list(reasoning_output.historical_note_candidates),
            styling_rule_candidates=list(reasoning_output.styling_rule_candidates),
            can_offer_visualization=reasoning_output.can_offer_visualization,
            suggested_cta=reasoning_output.suggested_cta,
            observability=dict(reasoning_output.observability),
        )
        generation_payload = GenerationHandoffPayload(
            generation_ready=reasoning_output.has_generation_handoff(),
            fashion_brief=reasoning_output.fashion_brief if reasoning_output.has_generation_handoff() else None,
            image_cta_candidates=list(reasoning_output.image_cta_candidates),
            blocked_reason=_blocked_reason(reasoning_output),
            observability=dict(reasoning_output.observability),
        )
        return FashionReasoningPresentationPayload(
            voice=voice_payload,
            generation=generation_payload,
            observability=dict(reasoning_output.observability),
        )


def _blocked_reason(reasoning_output: FashionReasoningOutput) -> str | None:
    if reasoning_output.has_generation_handoff():
        return None
    if reasoning_output.requires_clarification():
        return "clarification_required"
    if not reasoning_output.can_offer_visualization:
        return "visualization_not_offered"
    if reasoning_output.fashion_brief is None:
        return "fashion_brief_missing"
    if not reasoning_output.generation_ready:
        return "generation_not_ready"
    return "generation_handoff_unavailable"
