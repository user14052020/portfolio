from app.domain.reasoning import (
    FashionReasoningInput,
    FashionReasoningOutput,
    ImageCtaCandidate,
    ReasoningMetadata,
)


class DefaultFashionReasoner:
    async def reason(self, reasoning_input: FashionReasoningInput) -> FashionReasoningOutput:
        missing_slot = _missing_required_slot(reasoning_input)
        if missing_slot is not None:
            question = _clarification_question(missing_slot)
            observability = _observability(reasoning_input, clarification_required=True)
            return FashionReasoningOutput(
                response_type="clarification",
                text_response=question,
                clarification_question=question,
                can_offer_visualization=False,
                fashion_brief=None,
                generation_ready=False,
                reasoning_metadata=ReasoningMetadata.from_observability(observability),
                observability=observability,
            )

        style_logic_points = _collect_style_logic(reasoning_input)
        visual_language_points = _collect_visual_language(reasoning_input)
        historical_notes = _collect_historical_notes(reasoning_input)
        styling_rules = _collect_styling_rules(reasoning_input)
        image_strength = _image_context_strength(reasoning_input)
        can_offer_visualization = image_strength >= 2 and bool(visual_language_points)
        image_cta_candidates = _build_image_cta_candidates(
            reasoning_input=reasoning_input,
            image_strength=image_strength,
            can_offer_visualization=can_offer_visualization,
        )
        response_type = "visual_offer" if can_offer_visualization else "text"
        if reasoning_input.generation_intent and reasoning_input.can_generate_now and can_offer_visualization:
            response_type = "generation_ready"
        observability = _observability(
            reasoning_input,
            clarification_required=False,
            image_strength=image_strength,
            cta_offered=can_offer_visualization,
        )

        return FashionReasoningOutput(
            response_type=response_type,
            text_response=_text_response(
                reasoning_input=reasoning_input,
                style_logic_points=style_logic_points,
                visual_language_points=visual_language_points,
                can_offer_visualization=can_offer_visualization,
            ),
            style_logic_points=style_logic_points,
            visual_language_points=visual_language_points,
            historical_note_candidates=historical_notes,
            styling_rule_candidates=styling_rules,
            can_offer_visualization=can_offer_visualization,
            suggested_cta=image_cta_candidates[0].cta_text if image_cta_candidates else None,
            image_cta_candidates=image_cta_candidates,
            fashion_brief=None,
            generation_ready=False,
            reasoning_metadata=ReasoningMetadata.from_observability(observability),
            observability=observability,
        )


def _missing_required_slot(reasoning_input: FashionReasoningInput) -> str | None:
    active_slots = {key: value for key, value in reasoning_input.active_slots.items() if value}
    if reasoning_input.mode == "occasion_outfit" and "occasion" not in active_slots:
        return "occasion"
    if reasoning_input.mode == "occasion_outfit" and "weather" not in active_slots:
        return "weather"
    if reasoning_input.generation_intent and not reasoning_input.can_generate_now:
        return "generation_permission"
    return None


def _clarification_question(slot: str) -> str:
    questions = {
        "occasion": "What occasion should this outfit be built for?",
        "weather": "What weather or season should I account for?",
        "generation_permission": "Should I keep this as advice first, or prepare it for visualization?",
    }
    return questions.get(slot, "What detail should I use to narrow this down?")


def _collect_style_logic(reasoning_input: FashionReasoningInput) -> list[str]:
    items: list[str] = []
    for facet in reasoning_input.style_advice_facets:
        items.extend(facet.core_style_logic)
        items.extend(facet.casual_adaptations)
    for card in reasoning_input.style_context:
        if card.summary:
            items.append(card.summary)
    return _dedupe(items)[:6]


def _collect_styling_rules(reasoning_input: FashionReasoningInput) -> list[str]:
    items: list[str] = []
    for facet in reasoning_input.style_advice_facets:
        items.extend(facet.styling_rules)
        items.extend(facet.negative_guidance)
    return _dedupe(items)[:6]


def _collect_visual_language(reasoning_input: FashionReasoningInput) -> list[str]:
    items: list[str] = []
    for facet in reasoning_input.style_visual_language_facets:
        items.extend(facet.palette)
        items.extend(facet.lighting_mood)
        items.extend(facet.photo_treatment)
        items.extend(facet.visual_motifs)
    for facet in reasoning_input.style_image_facets:
        items.extend(facet.composition_cues)
    return _dedupe(items)[:8]


def _collect_historical_notes(reasoning_input: FashionReasoningInput) -> list[str]:
    items: list[str] = []
    for facet in reasoning_input.style_relation_facets:
        items.extend(facet.historical_relations)
        items.extend(facet.related_styles)
    for facet in reasoning_input.style_advice_facets:
        items.extend(facet.historical_notes)
    return _dedupe(items)[:5]


def _image_context_strength(reasoning_input: FashionReasoningInput) -> int:
    strength = 0
    for facet in reasoning_input.style_image_facets:
        if facet.hero_garments:
            strength += 1
        if facet.composition_cues:
            strength += 1
        if facet.props or facet.core_accessories:
            strength += 1
    for facet in reasoning_input.style_visual_language_facets:
        if facet.palette:
            strength += 1
        if facet.lighting_mood or facet.photo_treatment:
            strength += 1
    return strength


def _build_image_cta_candidates(
    *,
    reasoning_input: FashionReasoningInput,
    image_strength: int,
    can_offer_visualization: bool,
) -> list[ImageCtaCandidate]:
    if not can_offer_visualization:
        return []

    confidence = min(0.95, 0.45 + image_strength * 0.1)
    trigger = "generate_now" if reasoning_input.generation_intent and reasoning_input.can_generate_now else "offer_visualization"
    return [
        ImageCtaCandidate(
            cta_text="Visualize this direction",
            reason="The retrieved image and visual-language facets are specific enough for a visual handoff.",
            confidence=confidence,
            required_generation_trigger=trigger,
        )
    ]


def _text_response(
    *,
    reasoning_input: FashionReasoningInput,
    style_logic_points: list[str],
    visual_language_points: list[str],
    can_offer_visualization: bool,
) -> str:
    subject = reasoning_input.user_request.strip() if reasoning_input.user_request.strip() else "this request"
    style_part = style_logic_points[0] if style_logic_points else "I can shape this with a coherent style direction."
    visual_part = (
        f" Visually, I would lean on {visual_language_points[0]}."
        if visual_language_points
        else ""
    )
    cta_part = " I can also prepare this for visualization." if can_offer_visualization else ""
    return f"For {subject}, {style_part}{visual_part}{cta_part}"


def _observability(
    reasoning_input: FashionReasoningInput,
    *,
    clarification_required: bool,
    image_strength: int = 0,
    cta_offered: bool = False,
) -> dict[str, object]:
    return {
        "routing_mode": reasoning_input.mode,
        "retrieval_profile": reasoning_input.retrieval_profile,
        "providers_used": list(reasoning_input.knowledge_context.providers_used),
        "profile_alignment_applied": reasoning_input.profile_alignment_applied,
        "profile_alignment_notes": list(reasoning_input.profile_alignment_notes),
        "profile_alignment_filtered_count": len(reasoning_input.profile_alignment_filtered_out),
        "clarification_required": clarification_required,
        "fashion_brief_built": False,
        "cta_offered": cta_offered,
        "generation_ready": False,
        "image_context_strength": image_strength,
        **reasoning_input.observability_counts(),
    }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result
