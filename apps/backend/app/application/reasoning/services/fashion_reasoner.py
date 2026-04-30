from app.application.knowledge.contracts import KnowledgeRuntimeSettingsProvider
from app.application.reasoning.contracts import ProfileClarificationPolicy
from app.application.reasoning.services.profile_clarification_policy import (
    DefaultProfileClarificationPolicy,
)
from app.domain.knowledge.entities import KnowledgeRuntimeFlags
from app.domain.knowledge.enums import KnowledgeType
from app.domain.reasoning import (
    FashionReasoningInput,
    FashionReasoningOutput,
    ImageCtaCandidate,
    ProfileClarificationDecision,
    ReasoningMetadata,
)


class DefaultFashionReasoner:
    def __init__(
        self,
        *,
        profile_clarification_policy: ProfileClarificationPolicy | None = None,
        knowledge_runtime_flags: KnowledgeRuntimeFlags | None = None,
        knowledge_runtime_settings_provider: KnowledgeRuntimeSettingsProvider | None = None,
    ) -> None:
        self._profile_clarification_policy = (
            profile_clarification_policy or DefaultProfileClarificationPolicy()
        )
        self._knowledge_runtime_flags = knowledge_runtime_flags or KnowledgeRuntimeFlags()
        self._knowledge_runtime_settings_provider = knowledge_runtime_settings_provider

    async def reason(self, reasoning_input: FashionReasoningInput) -> FashionReasoningOutput:
        runtime_flags = await self._resolved_runtime_flags()
        missing_slot = _pre_profile_missing_slot(reasoning_input)
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

        profile_clarification = await self._profile_clarification_policy.evaluate(
            mode=reasoning_input.mode,
            profile=reasoning_input.profile_context,
            style_bundle=reasoning_input.style_facet_bundle(),
        )
        if profile_clarification.should_ask:
            question = profile_clarification.question_text or _clarification_question("profile")
            observability = _observability(
                reasoning_input,
                clarification_required=True,
                profile_clarification=profile_clarification,
            )
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

        missing_slot = _post_profile_missing_slot(reasoning_input)
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
        visual_language_points = _collect_visual_language(
            reasoning_input,
            runtime_flags,
        )
        historical_notes = _collect_historical_notes(
            reasoning_input,
            runtime_flags,
        )
        styling_rules = _collect_styling_rules(reasoning_input)
        editorial_context = _collect_editorial_context(
            reasoning_input,
            runtime_flags,
        )
        color_poetic_candidates = _collect_color_poetic_candidates(
            reasoning_input,
            runtime_flags,
        )
        composition_theory_candidates = _collect_composition_theory_candidates(
            reasoning_input,
            runtime_flags,
        )
        anti_repeat_related_style = _anti_repeat_related_style(reasoning_input)
        image_strength = _image_context_strength(reasoning_input)
        can_offer_visualization = image_strength >= 2 and bool(visual_language_points)
        image_cta_candidates = _build_image_cta_candidates(
            reasoning_input=reasoning_input,
            image_strength=image_strength,
            can_offer_visualization=can_offer_visualization,
        )
        cta_confidence_score = image_cta_candidates[0].confidence if image_cta_candidates else 0.0
        response_type = "visual_offer" if can_offer_visualization else "text"
        if reasoning_input.generation_intent and reasoning_input.can_generate_now and can_offer_visualization:
            response_type = "generation_ready"
        observability = _observability(
            reasoning_input,
            clarification_required=False,
            profile_clarification=profile_clarification,
            image_strength=image_strength,
            cta_offered=can_offer_visualization,
            has_visual_language=bool(visual_language_points),
            cta_confidence_score=cta_confidence_score,
            profile_signals_sufficient=_profile_signals_sufficient(reasoning_input),
            reasoning_is_mostly_advisory=_reasoning_is_mostly_advisory(reasoning_input),
        )

        return FashionReasoningOutput(
            response_type=response_type,
            text_response=_text_response(
                reasoning_input=reasoning_input,
                style_logic_points=style_logic_points,
                visual_language_points=visual_language_points,
                can_offer_visualization=can_offer_visualization,
                anti_repeat_related_style=anti_repeat_related_style,
            ),
            style_logic_points=style_logic_points,
            visual_language_points=visual_language_points,
            historical_note_candidates=historical_notes,
            styling_rule_candidates=styling_rules,
            editorial_context_candidates=editorial_context,
            color_poetic_candidates=color_poetic_candidates,
            composition_theory_candidates=composition_theory_candidates,
            can_offer_visualization=can_offer_visualization,
            suggested_cta=image_cta_candidates[0].cta_text if image_cta_candidates else None,
            image_cta_candidates=image_cta_candidates,
            fashion_brief=None,
            generation_ready=False,
            reasoning_metadata=ReasoningMetadata.from_observability(observability),
            observability=observability,
        )

    async def _resolved_runtime_flags(self) -> KnowledgeRuntimeFlags:
        if self._knowledge_runtime_settings_provider is None:
            return self._knowledge_runtime_flags
        return await self._knowledge_runtime_settings_provider.get_runtime_flags()


def _pre_profile_missing_slot(reasoning_input: FashionReasoningInput) -> str | None:
    active_slots = {key: value for key, value in reasoning_input.active_slots.items() if value}
    if reasoning_input.mode == "occasion_outfit" and "occasion" not in active_slots:
        return "occasion"
    if reasoning_input.mode == "occasion_outfit" and "weather" not in active_slots:
        return "weather"
    return None


def _post_profile_missing_slot(reasoning_input: FashionReasoningInput) -> str | None:
    if _requires_visual_intent_clarification(reasoning_input):
        return "visual_intent"
    if reasoning_input.generation_intent and not reasoning_input.can_generate_now:
        return "generation_permission"
    return None


def _clarification_question(slot: str) -> str:
    questions = {
        "occasion": "What occasion should this outfit be built for?",
        "weather": "What weather or season should I account for?",
        "silhouette_preference": "Do you prefer a relaxed, fitted, or oversized silhouette for this look?",
        "profile": "What profile detail should I use to tailor this direction more precisely?",
        "visual_intent": "Should I keep this as text advice, or shape it toward a visualizable outfit direction?",
        "generation_permission": "Should I keep this as advice first, or prepare it for visualization?",
    }
    return questions.get(slot, "What detail should I use to narrow this down?")


def _collect_style_logic(reasoning_input: FashionReasoningInput) -> list[str]:
    items: list[str] = []
    for facet in _ordered_advice_facets(reasoning_input):
        items.extend(facet.core_style_logic)
        items.extend(facet.casual_adaptations)
        items.extend(facet.overlap_context)
    for card in reasoning_input.knowledge_context.style_advice_cards:
        text = _knowledge_card_text(card)
        if text:
            items.append(text)
    items.extend(_semantic_fragment_summaries(reasoning_input, {"advice", "style_logic"}))
    for card in reasoning_input.style_context:
        if card.summary:
            items.append(card.summary)
    return _dedupe(items)[:6]


def _collect_styling_rules(reasoning_input: FashionReasoningInput) -> list[str]:
    items: list[str] = []
    for facet in _ordered_advice_facets(reasoning_input):
        items.extend(facet.styling_rules)
        items.extend(facet.negative_guidance)
    items.extend(_semantic_fragment_summaries(reasoning_input, {"styling_rule", "advice"}))
    return _dedupe(items)[:6]


def _collect_visual_language(
    reasoning_input: FashionReasoningInput,
    runtime_flags: KnowledgeRuntimeFlags,
) -> list[str]:
    items: list[str] = []
    repeated_visual_motifs = _history_visual_motifs(reasoning_input)
    avoided_palette = _avoid_terms(reasoning_input, "avoid_palette")
    avoided_compositions = _avoid_terms(reasoning_input, "avoid_composition_types")
    for facet in _ordered_visual_language_facets(reasoning_input):
        if runtime_flags.use_color_poetics:
            items.extend(
                item
                for item in facet.palette
                if item.strip() and item.strip().lower() not in avoided_palette
            )
            items.extend(facet.lighting_mood)
            items.extend(facet.photo_treatment)
        items.extend(facet.mood_keywords)
        items.extend(
            item
            for item in facet.visual_motifs
            if item.strip() and item.strip().lower() not in repeated_visual_motifs
        )
        items.extend(facet.platform_visual_cues)
    for facet in _ordered_image_facets(reasoning_input):
        items.extend(
            item
            for item in facet.composition_cues
            if item.strip() and not _matches_any(item, avoided_compositions)
        )
    for card in reasoning_input.knowledge_context.style_visual_cards:
        text = _knowledge_card_text(card)
        if text:
            items.append(text)
    items.extend(
        _semantic_fragment_summaries(
            reasoning_input,
            {"visual_language", "image_composition", "image", "composition"},
        )
    )
    return _dedupe(items)[:8]


def _collect_historical_notes(
    reasoning_input: FashionReasoningInput,
    runtime_flags: KnowledgeRuntimeFlags,
) -> list[str]:
    if not runtime_flags.use_historical_context:
        return []
    items: list[str] = []
    for facet in _ordered_relation_facets(reasoning_input):
        items.extend(facet.historical_relations)
        items.extend(facet.related_styles)
        items.extend(f"overlaps with {item}" for item in facet.overlap_styles if item.strip())
        items.extend(f"brand reference: {item}" for item in facet.brands if item.strip())
        items.extend(f"platform cue: {item}" for item in facet.platforms if item.strip())
    for facet in _ordered_advice_facets(reasoning_input):
        items.extend(facet.historical_notes)
    for card in reasoning_input.knowledge_context.knowledge_cards:
        if card.knowledge_type == KnowledgeType.FASHION_HISTORY:
            items.append(card.summary or card.title)
    if runtime_flags.use_editorial_knowledge:
        for card in reasoning_input.knowledge_context.editorial_cards:
            items.append(card.summary or card.title)
    items.extend(
        _semantic_fragment_summaries(
            reasoning_input,
            {"relations", "relation", "history", "historical"},
        )
    )
    return _dedupe(items)[:5]


def _collect_editorial_context(
    reasoning_input: FashionReasoningInput,
    runtime_flags: KnowledgeRuntimeFlags,
) -> list[str]:
    if not runtime_flags.use_editorial_knowledge:
        return []
    items: list[str] = []
    for card in reasoning_input.knowledge_context.editorial_cards:
        text = _knowledge_card_text(card)
        if text:
            items.append(text)
    return _dedupe(items)[:4]


def _collect_color_poetic_candidates(
    reasoning_input: FashionReasoningInput,
    runtime_flags: KnowledgeRuntimeFlags,
) -> list[str]:
    if not runtime_flags.use_color_poetics:
        return []
    items: list[str] = []
    for facet in _ordered_visual_language_facets(reasoning_input):
        items.extend(facet.palette)
        items.extend(facet.lighting_mood)
        items.extend(facet.photo_treatment)
    for card in reasoning_input.knowledge_context.knowledge_cards:
        if card.knowledge_type in _COLOR_POETIC_KNOWLEDGE_TYPES:
            text = _knowledge_card_text(card)
            if text:
                items.append(text)
    return _dedupe(items)[:6]


def _collect_composition_theory_candidates(
    reasoning_input: FashionReasoningInput,
    runtime_flags: KnowledgeRuntimeFlags,
) -> list[str]:
    if not runtime_flags.use_color_poetics:
        return []
    items: list[str] = []
    for facet in _ordered_image_facets(reasoning_input):
        items.extend(facet.composition_cues)
    for card in reasoning_input.knowledge_context.knowledge_cards:
        if card.knowledge_type in _COMPOSITION_THEORY_KNOWLEDGE_TYPES:
            text = _knowledge_card_text(card)
            if text:
                items.append(text)
    items.extend(
        _semantic_fragment_summaries(
            reasoning_input,
            {"image_composition", "composition"},
        )
    )
    return _dedupe(items)[:6]


def _image_context_strength(reasoning_input: FashionReasoningInput) -> int:
    strength = 0
    avoided_hero_garments = _avoid_terms(reasoning_input, "avoid_hero_garments")
    avoided_accessories = _avoid_terms(reasoning_input, "avoid_accessories")
    avoided_compositions = _avoid_terms(reasoning_input, "avoid_composition_types")
    for facet in _ordered_image_facets(reasoning_input):
        if _has_non_avoided_items(facet.hero_garments, avoided_hero_garments):
            strength += 1
        if _has_non_avoided_items(facet.composition_cues, avoided_compositions):
            strength += 1
        if _has_non_avoided_items([*facet.props, *facet.core_accessories], avoided_accessories):
            strength += 1
    for facet in _ordered_visual_language_facets(reasoning_input):
        if facet.palette:
            strength += 1
        if facet.lighting_mood or facet.photo_treatment or facet.mood_keywords:
            strength += 1
        if facet.visual_motifs or facet.platform_visual_cues:
            strength += 1
    if _semantic_fragment_summaries(reasoning_input, {"image_composition", "image", "composition"}):
        strength += 1
    if _semantic_fragment_summaries(reasoning_input, {"visual_language"}):
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

    confidence = 0.35 + image_strength * 0.08
    if reasoning_input.generation_intent:
        confidence += 0.15
    if reasoning_input.visual_intent_signal == "open_to_visualization":
        confidence += 0.08
    elif reasoning_input.visual_intent_signal == "advice_only":
        confidence -= 0.06
    if _profile_signals_sufficient(reasoning_input):
        confidence += 0.08
    else:
        confidence -= 0.05
    if _reasoning_is_mostly_advisory(reasoning_input):
        confidence -= 0.1
    confidence = max(0.25, min(0.95, confidence))
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
    anti_repeat_related_style: str | None,
) -> str:
    subject = reasoning_input.user_request.strip() if reasoning_input.user_request.strip() else "this request"
    style_part = style_logic_points[0] if style_logic_points else "I can shape this with a coherent style direction."
    direction_part = (
        f"shift toward {anti_repeat_related_style}. "
        if anti_repeat_related_style
        else ""
    )
    visual_part = (
        f" Visually, I would lean on {visual_language_points[0]}."
        if visual_language_points
        else ""
    )
    cta_part = " I can also prepare this for visualization." if can_offer_visualization else ""
    return f"For {subject}, {direction_part}{style_part}{visual_part}{cta_part}"


def _observability(
    reasoning_input: FashionReasoningInput,
    *,
    clarification_required: bool,
    profile_clarification: ProfileClarificationDecision | None = None,
    image_strength: int = 0,
    cta_offered: bool = False,
    has_visual_language: bool = False,
    cta_confidence_score: float = 0.0,
    profile_signals_sufficient: bool = False,
    reasoning_is_mostly_advisory: bool = False,
) -> dict[str, object]:
    cta_blocked_reasons = _cta_blocked_reasons(
        clarification_required=clarification_required,
        image_strength=image_strength,
        has_visual_language=has_visual_language,
    )
    return {
        "routing_mode": reasoning_input.mode,
        "retrieval_profile": reasoning_input.retrieval_profile,
        "providers_used": list(reasoning_input.knowledge_context.providers_used),
        "profile_alignment_applied": reasoning_input.profile_alignment_applied,
        "profile_alignment_notes": list(reasoning_input.profile_alignment_notes),
        "profile_alignment_filtered_count": len(reasoning_input.profile_alignment_filtered_out),
        "profile_alignment_boosted_categories": list(
            reasoning_input.profile_alignment_boosted_categories
        ),
        "profile_alignment_removed_item_types": list(
            reasoning_input.profile_alignment_removed_item_types
        ),
        "clarification_required": clarification_required,
        "fashion_brief_built": False,
        "cta_offered": cta_offered,
        "cta_decision_reason": _cta_decision_reason(
            cta_offered=cta_offered,
            cta_blocked_reasons=cta_blocked_reasons,
        ),
        "cta_blocked_reasons": cta_blocked_reasons,
        "cta_confidence_score": cta_confidence_score,
        "profile_signals_sufficient": profile_signals_sufficient,
        "reasoning_is_mostly_advisory": reasoning_is_mostly_advisory,
        "generation_ready": False,
        "visual_intent_signal_present": (
            reasoning_input.generation_intent or reasoning_input.visual_intent_signal is not None
        ),
        "visual_intent_required": reasoning_input.visual_intent_required,
        "visual_intent_signal": reasoning_input.visual_intent_signal,
        "profile_completeness_state": _profile_completeness_state(reasoning_input),
        "profile_clarification_decision": _profile_clarification_decision(
            clarification_required=clarification_required,
            profile_clarification=profile_clarification,
        ),
        "profile_clarification_required": bool(
            clarification_required and profile_clarification is not None and profile_clarification.should_ask
        ),
        "profile_clarification_missing_priority_fields": (
            list(profile_clarification.missing_priority_fields)
            if profile_clarification is not None
            else []
        ),
        "image_context_strength": image_strength,
        "anti_repeat_related_style_selected": _anti_repeat_related_style(reasoning_input),
        "anti_repeat_hero_garments_avoided_count": _anti_repeat_image_cue_hits(
            reasoning_input,
            field_name="hero_garments",
            avoid_field="avoid_hero_garments",
        ),
        "anti_repeat_accessories_avoided_count": _anti_repeat_image_cue_hits(
            reasoning_input,
            field_name="accessories",
            avoid_field="avoid_accessories",
        ),
        "anti_repeat_composition_cues_avoided_count": _anti_repeat_image_cue_hits(
            reasoning_input,
            field_name="composition_cues",
            avoid_field="avoid_composition_types",
        ),
        "anti_repeat_visual_motifs_avoided_count": _anti_repeat_visual_motif_hits(reasoning_input),
        **reasoning_input.observability_counts(),
    }


def _cta_blocked_reasons(
    *,
    clarification_required: bool,
    image_strength: int,
    has_visual_language: bool,
) -> list[str]:
    if clarification_required:
        return ["clarification_required"]
    blockers: list[str] = []
    if image_strength < 2:
        blockers.append("insufficient_image_context")
    if not has_visual_language:
        blockers.append("missing_visual_language")
    return blockers


def _cta_decision_reason(*, cta_offered: bool, cta_blocked_reasons: list[str]) -> str:
    if cta_offered:
        return "image_context_and_visual_language_sufficient"
    if cta_blocked_reasons:
        return cta_blocked_reasons[0]
    return "visualization_not_offered"


def _profile_clarification_decision(
    *,
    clarification_required: bool,
    profile_clarification: ProfileClarificationDecision | None,
) -> str:
    if profile_clarification is None:
        return "not_profile_related" if clarification_required else "not_needed"
    if profile_clarification.should_ask and clarification_required:
        return "asked"
    if profile_clarification.should_ask:
        return "ready_but_not_used"
    return "skipped"


def _semantic_fragment_summaries(reasoning_input: FashionReasoningInput, fragment_types: set[str]) -> list[str]:
    values: list[str] = []
    normalized_types = {item.lower().strip() for item in fragment_types}
    for fragment in reasoning_input.style_semantic_fragments:
        fragment_type = fragment.fragment_type.lower().strip()
        if fragment_type in normalized_types and fragment.summary.strip():
            values.append(fragment.summary)
    return values


def _anti_repeat_requested(reasoning_input: FashionReasoningInput) -> bool:
    request = reasoning_input.user_request.lower()
    return any(
        marker in request
        for marker in (
            "another",
            "different",
            "adjacent",
            "without repeating",
            "without repeat",
            "new direction",
        )
    )


def _anti_repeat_related_style(reasoning_input: FashionReasoningInput) -> str | None:
    if not _anti_repeat_requested(reasoning_input):
        return None
    recent_labels = _recent_style_labels(reasoning_input)
    for facet in _ordered_relation_facets(reasoning_input):
        for candidate in [*facet.related_styles, *facet.overlap_styles]:
            cleaned = candidate.strip()
            if cleaned and cleaned.lower() not in recent_labels:
                return cleaned
    return None


def _recent_style_labels(reasoning_input: FashionReasoningInput) -> set[str]:
    labels: set[str] = set()
    for item in reasoning_input.style_history:
        for label in (item.style_name, item.style_cluster):
            if label and label.strip():
                labels.add(label.strip().lower())
    for card in reasoning_input.knowledge_context.style_history_cards:
        metadata = getattr(card, "metadata", {}) or {}
        for label in (
            getattr(card, "title", None),
            metadata.get("style_name"),
            metadata.get("style_cluster"),
        ):
            if isinstance(label, str) and label.strip():
                labels.add(label.strip().lower())
    for card in reasoning_input.style_context:
        if card.title.strip():
            labels.add(card.title.strip().lower())
    return labels


def _history_visual_motifs(reasoning_input: FashionReasoningInput) -> set[str]:
    motifs: set[str] = set()
    for item in reasoning_input.style_history:
        for motif in item.visual_motifs:
            cleaned = motif.strip().lower()
            if cleaned:
                motifs.add(cleaned)
    for card in reasoning_input.knowledge_context.style_history_cards:
        metadata = getattr(card, "metadata", {}) or {}
        for motif in metadata.get("visual_motifs", []):
            cleaned = str(motif).strip().lower()
            if cleaned:
                motifs.add(cleaned)
    return motifs


def _anti_repeat_visual_motif_hits(reasoning_input: FashionReasoningInput) -> int:
    history_motifs = _history_visual_motifs(reasoning_input)
    if not history_motifs:
        return 0
    hits = {
        item.strip().lower()
        for facet in _ordered_visual_language_facets(reasoning_input)
        for item in facet.visual_motifs
        if item.strip().lower() in history_motifs
    }
    return len(hits)


def _anti_repeat_image_cue_hits(
    reasoning_input: FashionReasoningInput,
    *,
    field_name: str,
    avoid_field: str,
) -> int:
    avoid_terms = _avoid_terms(reasoning_input, avoid_field)
    if not avoid_terms:
        return 0
    hits: set[str] = set()
    for facet in _ordered_image_facets(reasoning_input):
        if field_name == "hero_garments":
            items = facet.hero_garments
        elif field_name == "composition_cues":
            items = facet.composition_cues
        else:
            items = [*facet.props, *facet.core_accessories]
        for item in items:
            cleaned = item.strip().lower()
            if cleaned and _matches_any(item, avoid_terms):
                hits.add(cleaned)
    return len(hits)


def _avoid_terms(reasoning_input: FashionReasoningInput, field_name: str) -> set[str]:
    if reasoning_input.diversity_constraints is None:
        return set()
    values = getattr(reasoning_input.diversity_constraints, field_name, [])
    return {
        str(item).strip().lower()
        for item in values
        if str(item).strip()
    }


def _has_silhouette_preference(reasoning_input: FashionReasoningInput) -> bool:
    for key in ("silhouette", "preferred_silhouette", "fit", "fit_preference"):
        value = reasoning_input.active_slots.get(key)
        if isinstance(value, str) and value.strip():
            return True
    if reasoning_input.profile_context is None or not reasoning_input.profile_context.present:
        return False
    for key in ("silhouette", "preferred_silhouette", "fit", "fit_preference"):
        value = reasoning_input.profile_context.values.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def _profile_completeness_state(reasoning_input: FashionReasoningInput) -> str:
    profile = reasoning_input.profile_context
    if profile is None or not profile.present:
        return "missing"
    important_signals = 0
    if profile.presentation_profile:
        important_signals += 1
    if profile.fit_preferences or profile.silhouette_preferences:
        important_signals += 1
    if profile.comfort_preferences or profile.formality_preferences:
        important_signals += 1
    if important_signals >= 3:
        return "strong"
    if important_signals >= 1:
        return "partial"
    return "missing"


def _profile_signals_sufficient(reasoning_input: FashionReasoningInput) -> bool:
    if reasoning_input.profile_alignment_applied and reasoning_input.profile_facet_weights:
        return True
    if reasoning_input.profile_context is not None and reasoning_input.profile_context.present:
        if reasoning_input.profile_context.values:
            return True
    if reasoning_input.mode == "occasion_outfit" and _has_silhouette_preference(reasoning_input):
        return True
    return False


def _reasoning_is_mostly_advisory(reasoning_input: FashionReasoningInput) -> bool:
    if reasoning_input.generation_intent:
        return False
    if reasoning_input.visual_intent_signal == "open_to_visualization":
        return False
    if reasoning_input.visual_intent_signal == "advice_only":
        return True
    return reasoning_input.mode == "general_advice" or reasoning_input.retrieval_profile in {
        "light",
        "style_focused",
        "occasion_focused",
    }


def _requires_visual_intent_clarification(reasoning_input: FashionReasoningInput) -> bool:
    return (
        reasoning_input.visual_intent_required
        and reasoning_input.visual_intent_signal is None
        and not reasoning_input.generation_intent
    )


def _ordered_advice_facets(reasoning_input: FashionReasoningInput):
    return _ordered_facets(reasoning_input.style_advice_facets, reasoning_input, "advice")


def _ordered_image_facets(reasoning_input: FashionReasoningInput):
    return _ordered_facets(reasoning_input.style_image_facets, reasoning_input, "image")


def _ordered_visual_language_facets(reasoning_input: FashionReasoningInput):
    return _ordered_facets(reasoning_input.style_visual_language_facets, reasoning_input, "visual")


def _ordered_relation_facets(reasoning_input: FashionReasoningInput):
    return _ordered_facets(reasoning_input.style_relation_facets, reasoning_input, "relation")


def _knowledge_card_text(card) -> str | None:
    compact_text = getattr(card, "compact_text", None)
    if callable(compact_text):
        text = compact_text()
        if isinstance(text, str) and text.strip():
            return text.strip()
    for value in (getattr(card, "summary", None), getattr(card, "title", None)):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _ordered_facets(facets, reasoning_input: FashionReasoningInput, prefix: str):
    return sorted(
        facets,
        key=lambda facet: _facet_weight(reasoning_input, prefix, getattr(facet, "style_id", None)),
        reverse=True,
    )


def _facet_weight(reasoning_input: FashionReasoningInput, prefix: str, style_id: object) -> float:
    key = f"{prefix}:{style_id}"
    raw_value = reasoning_input.profile_facet_weights.get(key)
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    return 1.0


def _has_non_avoided_items(items: list[str], avoid_terms: set[str]) -> bool:
    for item in items:
        cleaned = item.strip()
        if cleaned and not _matches_any(cleaned, avoid_terms):
            return True
    return False


def _matches_any(text: str, terms: set[str]) -> bool:
    lowered = text.strip().lower()
    return any(term in lowered for term in terms)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


_COLOR_POETIC_KNOWLEDGE_TYPES = {
    KnowledgeType.COLOR_THEORY,
    KnowledgeType.LIGHT_THEORY,
    KnowledgeType.STYLE_PALETTE_LOGIC,
    KnowledgeType.STYLE_PHOTO_TREATMENT,
}

_COMPOSITION_THEORY_KNOWLEDGE_TYPES = {
    KnowledgeType.COMPOSITION_THEORY,
    KnowledgeType.STYLE_IMAGE_COMPOSITION,
}
