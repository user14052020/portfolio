from typing import Any

from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.reasoning import FashionReasoningInput, FashionReasoningOutput


class DefaultFashionBriefBuilder:
    async def build(
        self,
        *,
        reasoning_input: FashionReasoningInput,
        reasoning_output: FashionReasoningOutput,
    ) -> FashionBrief:
        style_identity = _style_identity(reasoning_input)
        hero_garments = _dedupe(
            [item for facet in reasoning_input.style_image_facets for item in facet.hero_garments]
        )
        secondary_garments = _dedupe(
            [item for facet in reasoning_input.style_image_facets for item in facet.secondary_garments]
        )
        accessories = _dedupe(
            [item for facet in reasoning_input.style_image_facets for item in facet.core_accessories]
        )
        props = _dedupe([item for facet in reasoning_input.style_image_facets for item in facet.props])
        palette = _dedupe(
            [item for facet in reasoning_input.style_visual_language_facets for item in facet.palette]
        )
        hero_garments = _without_avoided(hero_garments, _avoid_terms(reasoning_input, "avoid_hero_garments"))
        secondary_garments = _without_avoided(
            secondary_garments,
            _avoid_terms(reasoning_input, "avoid_hero_garments"),
        )
        palette = _without_avoided(palette, _avoid_terms(reasoning_input, "avoid_palette"))
        accessories = _without_avoided(accessories, _avoid_terms(reasoning_input, "avoid_accessories"))
        photo_treatment = _dedupe(
            [
                item
                for facet in reasoning_input.style_visual_language_facets
                for item in facet.photo_treatment
            ]
        )
        lighting_mood = _dedupe(
            [
                item
                for facet in reasoning_input.style_visual_language_facets
                for item in facet.lighting_mood
            ]
        )
        visual_motifs = _dedupe(
            [
                item
                for facet in reasoning_input.style_visual_language_facets
                for item in facet.visual_motifs
            ]
        )
        composition_rules = _dedupe(
            [item for facet in reasoning_input.style_image_facets for item in facet.composition_cues]
        )
        negative_constraints = _dedupe(
            [
                *[item for facet in reasoning_input.style_image_facets for item in facet.negative_constraints],
                *[item for facet in reasoning_input.style_advice_facets for item in facet.negative_guidance],
                *_anti_repeat_negative_constraints(reasoning_input),
            ]
        )

        return FashionBrief(
            intent=reasoning_input.mode,
            style_direction=style_identity,
            style_identity=style_identity,
            style_family=_style_family(reasoning_input),
            brief_mode=reasoning_input.mode,
            historical_reference=list(reasoning_output.historical_note_candidates),
            tailoring_logic=list(reasoning_output.style_logic_points),
            color_logic=_color_logic(reasoning_input, reasoning_output, palette),
            silhouette=_silhouette(reasoning_input),
            hero_garments=hero_garments,
            secondary_garments=secondary_garments,
            garment_list=_dedupe([*hero_garments, *secondary_garments]),
            palette=palette,
            accessories=accessories,
            props=props,
            visual_motifs=visual_motifs,
            lighting_mood=lighting_mood,
            styling_notes=list(reasoning_output.styling_rule_candidates),
            composition_rules=composition_rules,
            photo_treatment=photo_treatment,
            negative_constraints=negative_constraints,
            diversity_constraints=_diversity_constraints(reasoning_input),
            generation_intent="requested" if reasoning_input.generation_intent else "optional",
            knowledge_cards=_knowledge_cards(reasoning_input),
            source_style_facet_ids=_source_style_facet_ids(reasoning_input),
            brief_confidence=_brief_confidence(reasoning_input, reasoning_output),
            metadata={
                "response_type": reasoning_output.response_type,
                "retrieval_profile": reasoning_input.retrieval_profile,
                "providers_used": list(reasoning_input.knowledge_context.providers_used),
                "can_offer_visualization": reasoning_output.can_offer_visualization,
                "suggested_cta": reasoning_output.suggested_cta,
            },
        )


def _style_identity(reasoning_input: FashionReasoningInput) -> str:
    for card in reasoning_input.style_context:
        if card.title.strip():
            return card.title.strip()
    for facet in reasoning_input.style_relation_facets:
        if facet.related_styles:
            return facet.related_styles[0]
    return reasoning_input.user_request.strip() or "Fashion direction"


def _style_family(reasoning_input: FashionReasoningInput) -> str | None:
    for facet in reasoning_input.style_relation_facets:
        if facet.overlap_styles:
            return facet.overlap_styles[0]
        if facet.related_styles:
            return facet.related_styles[0]
    return None


def _color_logic(
    reasoning_input: FashionReasoningInput,
    reasoning_output: FashionReasoningOutput,
    filtered_palette: list[str],
) -> list[str]:
    visual_points = list(reasoning_output.visual_language_points)
    color_logic = _dedupe([*filtered_palette, *visual_points])[:8]
    return _without_avoided(color_logic, _avoid_terms(reasoning_input, "avoid_palette"))


def _silhouette(reasoning_input: FashionReasoningInput) -> str | None:
    for key in ("silhouette", "preferred_silhouette", "fit", "fit_preference"):
        value = reasoning_input.active_slots.get(key)
        if value and value.strip():
            return value.strip()
    if reasoning_input.profile_context is not None:
        for key in ("silhouette", "preferred_silhouette", "fit", "fit_preference"):
            value = reasoning_input.profile_context.values.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _diversity_constraints(reasoning_input: FashionReasoningInput) -> dict[str, Any]:
    if reasoning_input.diversity_constraints is None:
        return {}
    return reasoning_input.diversity_constraints.to_reasoning_dict()


def _avoid_terms(reasoning_input: FashionReasoningInput, field_name: str) -> list[str]:
    if reasoning_input.diversity_constraints is None:
        return []
    value = getattr(reasoning_input.diversity_constraints, field_name, [])
    return [str(item).strip().lower() for item in value if str(item).strip()]


def _without_avoided(items: list[str], avoid_terms: list[str]) -> list[str]:
    if not avoid_terms:
        return items
    return [item for item in items if not any(term in item.lower() for term in avoid_terms)]


def _anti_repeat_negative_constraints(reasoning_input: FashionReasoningInput) -> list[str]:
    if reasoning_input.diversity_constraints is None:
        return []
    constraints = reasoning_input.diversity_constraints
    notes: list[str] = []
    notes.extend(f"avoid recently used palette: {item}" for item in constraints.avoid_palette)
    notes.extend(f"avoid recently used hero garment: {item}" for item in constraints.avoid_hero_garments)
    notes.extend(f"avoid recently used accessory: {item}" for item in constraints.avoid_accessories)
    notes.extend(f"avoid recently used material: {item}" for item in constraints.avoid_materials)
    notes.extend(f"avoid recently used composition: {item}" for item in constraints.avoid_composition_types)
    return notes


def _knowledge_cards(reasoning_input: FashionReasoningInput) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for card in reasoning_input.knowledge_context.all_cards():
        cards.append(card.model_dump(mode="json"))
    return cards


def _source_style_facet_ids(reasoning_input: FashionReasoningInput) -> list[str]:
    ids: list[str] = []
    ids.extend(f"advice:{facet.style_id}" for facet in reasoning_input.style_advice_facets)
    ids.extend(f"image:{facet.style_id}" for facet in reasoning_input.style_image_facets)
    ids.extend(f"visual:{facet.style_id}" for facet in reasoning_input.style_visual_language_facets)
    ids.extend(f"relation:{facet.style_id}" for facet in reasoning_input.style_relation_facets)
    return _dedupe(ids)


def _brief_confidence(
    reasoning_input: FashionReasoningInput,
    reasoning_output: FashionReasoningOutput,
) -> float:
    score = 0.35
    if reasoning_input.style_advice_facets:
        score += 0.15
    if reasoning_input.style_image_facets:
        score += 0.15
    if reasoning_input.style_visual_language_facets:
        score += 0.15
    if reasoning_output.can_offer_visualization:
        score += 0.1
    if reasoning_input.knowledge_context.providers_used:
        score += 0.1
    return min(score, 0.95)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result
