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
        statement_pieces = _dedupe(
            [item for facet in _ordered_advice_facets(reasoning_input) for item in facet.statement_pieces]
        )
        status_markers = _dedupe(
            [item for facet in _ordered_advice_facets(reasoning_input) for item in facet.status_markers]
        )
        hero_garments = _dedupe(
            [item for facet in _ordered_image_facets(reasoning_input) for item in facet.hero_garments]
        )
        secondary_garments = _dedupe(
            [
                *[
                    item
                    for facet in _ordered_image_facets(reasoning_input)
                    for item in facet.secondary_garments
                ],
                *_wardrobe_items(statement_pieces),
            ]
        )
        accessories = _dedupe(
            [
                *[
                    item
                    for facet in _ordered_image_facets(reasoning_input)
                    for item in facet.core_accessories
                ],
                *_accessory_items(status_markers),
            ]
        )
        footwear = _dedupe(_footwear_items([*statement_pieces, *status_markers]))
        materials = _dedupe(_material_terms(_brief_source_texts(reasoning_input)))
        props = _dedupe([item for facet in _ordered_image_facets(reasoning_input) for item in facet.props])
        palette = _dedupe(
            [item for facet in _ordered_visual_language_facets(reasoning_input) for item in facet.palette]
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
                for facet in _ordered_visual_language_facets(reasoning_input)
                for item in facet.photo_treatment
            ]
        )
        mood_keywords = _dedupe(
            [
                item
                for facet in _ordered_visual_language_facets(reasoning_input)
                for item in facet.mood_keywords
            ]
        )
        platform_visual_cues = _dedupe(
            [
                item
                for facet in _ordered_visual_language_facets(reasoning_input)
                for item in facet.platform_visual_cues
            ]
        )
        lighting_mood = _dedupe(
            [
                item
                for facet in _ordered_visual_language_facets(reasoning_input)
                for item in facet.lighting_mood
            ]
        )
        visual_motifs = _dedupe(
            [
                item
                for facet in _ordered_visual_language_facets(reasoning_input)
                for item in facet.visual_motifs
            ]
        )
        visual_motifs = _without_avoided(
            visual_motifs,
            [item.lower() for item in _history_visual_motifs(reasoning_input)],
        )
        composition_rules = _dedupe(
            [
                *[
                    item
                    for facet in _ordered_image_facets(reasoning_input)
                    for item in facet.composition_cues
                ],
                *platform_visual_cues,
                *list(reasoning_output.visual_language_points),
            ]
        )
        negative_constraints = _dedupe(
            [
                *[
                    item
                    for facet in _ordered_image_facets(reasoning_input)
                    for item in facet.negative_constraints
                ],
                *[
                    item
                    for facet in _ordered_advice_facets(reasoning_input)
                    for item in facet.negative_guidance
                ],
                *_profile_alignment_negative_constraints(reasoning_input),
                *_anti_repeat_negative_constraints(reasoning_input),
            ]
        )

        return FashionBrief(
            intent=reasoning_input.mode,
            style_direction=style_identity,
            style_identity=style_identity,
            style_family=_style_family(reasoning_input),
            brief_mode=reasoning_input.mode,
            occasion_context=_occasion_context(reasoning_input),
            anchor_garment=_anchor_garment(hero_garments),
            historical_reference=list(reasoning_output.historical_note_candidates),
            tailoring_logic=list(reasoning_output.style_logic_points),
            color_logic=_color_logic(reasoning_input, reasoning_output, palette),
            silhouette=_silhouette(reasoning_input),
            hero_garments=hero_garments,
            secondary_garments=secondary_garments,
            garment_list=_dedupe([*hero_garments, *secondary_garments]),
            palette=palette,
            materials=materials,
            footwear=footwear,
            accessories=accessories,
            props=props,
            visual_motifs=visual_motifs,
            lighting_mood=lighting_mood,
            styling_notes=list(reasoning_output.styling_rule_candidates),
            composition_rules=composition_rules,
            photo_treatment=photo_treatment,
            negative_constraints=negative_constraints,
            diversity_constraints=_diversity_constraints(reasoning_input),
            visual_preset=_visual_preset(reasoning_input),
            generation_intent="requested" if reasoning_input.generation_intent else "optional",
            profile_constraints=_profile_constraints(reasoning_input),
            profile_context_snapshot=_profile_context_snapshot_payload(reasoning_input),
            knowledge_cards=_knowledge_cards(reasoning_input),
            source_style_facet_ids=_source_style_facet_ids(reasoning_input),
            brief_confidence=_brief_confidence(reasoning_input, reasoning_output),
            metadata={
                "response_type": reasoning_output.response_type,
                "retrieval_profile": reasoning_input.retrieval_profile,
                "providers_used": list(reasoning_input.knowledge_context.providers_used),
                "can_offer_visualization": reasoning_output.can_offer_visualization,
                "suggested_cta": reasoning_output.suggested_cta,
                "mood_keywords": mood_keywords,
                "platform_visual_cues": platform_visual_cues,
                "brand_references": _relation_brands(reasoning_input),
                "platform_references": _relation_platforms(reasoning_input),
                "overlap_contexts": _overlap_contexts(reasoning_input),
            },
        )


def _style_identity(reasoning_input: FashionReasoningInput) -> str:
    anti_repeat_style = _anti_repeat_related_style(reasoning_input)
    if anti_repeat_style is not None:
        return anti_repeat_style
    for card in reasoning_input.style_context:
        if card.title.strip():
            return card.title.strip()
    for facet in _ordered_relation_facets(reasoning_input):
        if facet.related_styles:
            return facet.related_styles[0]
    return reasoning_input.user_request.strip() or "Fashion direction"


def _style_family(reasoning_input: FashionReasoningInput) -> str | None:
    for facet in _ordered_relation_facets(reasoning_input):
        if facet.overlap_styles:
            return facet.overlap_styles[0]
        if facet.related_styles:
            return facet.related_styles[0]
    return None


def _occasion_context(reasoning_input: FashionReasoningInput) -> dict[str, Any] | None:
    if reasoning_input.mode != "occasion_outfit":
        return None
    values: dict[str, Any] = {}
    slot_mapping = {
        "occasion": "event_type",
        "event_type": "event_type",
        "location": "location",
        "time_of_day": "time_of_day",
        "season": "season",
        "dress_code": "dress_code",
        "weather": "weather_context",
        "weather_context": "weather_context",
        "desired_impression": "desired_impression",
    }
    for source_key, target_key in slot_mapping.items():
        value = reasoning_input.active_slots.get(source_key)
        if isinstance(value, str) and value.strip():
            values[target_key] = value.strip()
    if reasoning_input.profile_context is not None:
        profile_values = reasoning_input.profile_context.values
        for source_key, target_key in slot_mapping.items():
            if target_key in values:
                continue
            value = profile_values.get(source_key)
            if isinstance(value, str) and value.strip():
                values[target_key] = value.strip()
        for source_key in ("constraints", "color_preferences", "garment_preferences", "comfort_requirements"):
            if source_key in values:
                continue
            value = profile_values.get(source_key)
            if isinstance(value, list):
                items = [str(item).strip() for item in value if str(item).strip()]
                if items:
                    values[source_key] = items
    if not values:
        return None
    return values


def _anchor_garment(hero_garments: list[str]) -> dict[str, Any] | None:
    if not hero_garments:
        return None
    return {"name": hero_garments[0], "source": "hero_garments"}


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


def _visual_preset(reasoning_input: FashionReasoningInput) -> str | None:
    if reasoning_input.diversity_constraints is None:
        return None
    value = reasoning_input.diversity_constraints.suggested_visual_preset
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


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
    notes: list[str] = []
    if reasoning_input.diversity_constraints is not None:
        constraints = reasoning_input.diversity_constraints
        notes.extend(f"avoid recently used palette: {item}" for item in constraints.avoid_palette)
        notes.extend(f"avoid recently used hero garment: {item}" for item in constraints.avoid_hero_garments)
        notes.extend(f"avoid recently used accessory: {item}" for item in constraints.avoid_accessories)
        notes.extend(f"avoid recently used material: {item}" for item in constraints.avoid_materials)
        notes.extend(f"avoid recently used composition: {item}" for item in constraints.avoid_composition_types)
    notes.extend(
        f"avoid previously shown visual motif: {item}"
        for item in _history_visual_motifs(reasoning_input)
    )
    return notes


def _profile_alignment_negative_constraints(reasoning_input: FashionReasoningInput) -> list[str]:
    return [
        f"avoid profile-conflicting element: {item}"
        for item in reasoning_input.profile_alignment_filtered_out
        if item.strip()
    ]


def _knowledge_cards(reasoning_input: FashionReasoningInput) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for card in reasoning_input.knowledge_context.all_cards():
        cards.append(card.model_dump(mode="json"))
    return cards


def _profile_constraints(reasoning_input: FashionReasoningInput) -> dict[str, Any]:
    snapshot = reasoning_input.profile_context
    if snapshot is None or not snapshot.present:
        return {}
    constraints = {
        "presentation_profile": snapshot.presentation_profile,
        "fit_preferences": list(snapshot.fit_preferences),
        "silhouette_preferences": list(snapshot.silhouette_preferences),
        "comfort_preferences": list(snapshot.comfort_preferences),
        "formality_preferences": list(snapshot.formality_preferences),
        "color_preferences": list(snapshot.color_preferences),
        "color_avoidances": list(snapshot.color_avoidances),
        "preferred_items": list(snapshot.preferred_items),
        "avoided_items": list(snapshot.avoided_items),
    }
    return {key: value for key, value in constraints.items() if value}


def _profile_context_snapshot_payload(reasoning_input: FashionReasoningInput) -> dict[str, Any] | None:
    snapshot = reasoning_input.profile_context
    if snapshot is None:
        return None
    return {
        "present": snapshot.present,
        "source": snapshot.source,
        "values": dict(snapshot.values),
        **_profile_constraints(reasoning_input),
    }


def _source_style_facet_ids(reasoning_input: FashionReasoningInput) -> list[str]:
    ids: list[str] = []
    ids.extend(f"advice:{facet.style_id}" for facet in _ordered_advice_facets(reasoning_input))
    ids.extend(f"image:{facet.style_id}" for facet in _ordered_image_facets(reasoning_input))
    ids.extend(f"visual:{facet.style_id}" for facet in _ordered_visual_language_facets(reasoning_input))
    ids.extend(f"relation:{facet.style_id}" for facet in _ordered_relation_facets(reasoning_input))
    return _dedupe(ids)


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


def _history_visual_motifs(reasoning_input: FashionReasoningInput) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in reasoning_input.style_history:
        for motif in item.visual_motifs:
            cleaned = motif.strip()
            lowered = cleaned.lower()
            if cleaned and lowered not in seen:
                seen.add(lowered)
                result.append(cleaned)
    for card in reasoning_input.knowledge_context.style_history_cards:
        metadata = getattr(card, "metadata", {}) or {}
        for motif in metadata.get("visual_motifs", []):
            cleaned = str(motif).strip()
            lowered = cleaned.lower()
            if cleaned and lowered not in seen:
                seen.add(lowered)
                result.append(cleaned)
    return result


def _wardrobe_items(items: list[str]) -> list[str]:
    return [item for item in items if not _is_footwear(item) and not _is_accessory(item)]


def _footwear_items(items: list[str]) -> list[str]:
    return [item for item in items if _is_footwear(item)]


def _accessory_items(items: list[str]) -> list[str]:
    return [item for item in items if _is_accessory(item) and not _is_footwear(item)]


def _is_footwear(item: str) -> bool:
    lowered = item.lower()
    return any(term in lowered for term in _FOOTWEAR_TERMS)


def _is_accessory(item: str) -> bool:
    lowered = item.lower()
    return any(term in lowered for term in _ACCESSORY_TERMS)


def _brief_source_texts(reasoning_input: FashionReasoningInput) -> list[str]:
    texts: list[str] = []
    for facet in _ordered_advice_facets(reasoning_input):
        texts.extend(facet.core_style_logic)
        texts.extend(facet.styling_rules)
        texts.extend(facet.casual_adaptations)
        texts.extend(facet.statement_pieces)
        texts.extend(facet.status_markers)
    for facet in _ordered_image_facets(reasoning_input):
        texts.extend(facet.hero_garments)
        texts.extend(facet.secondary_garments)
        texts.extend(facet.core_accessories)
        texts.extend(facet.props)
    for fragment in reasoning_input.style_semantic_fragments:
        texts.append(fragment.summary)
    return texts


def _material_terms(texts: list[str]) -> list[str]:
    found: list[str] = []
    for text in texts:
        lowered = text.lower()
        found.extend(term for term in _MATERIAL_TERMS if term in lowered)
    return found


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


def _relation_brands(reasoning_input: FashionReasoningInput) -> list[str]:
    return _dedupe([item for facet in _ordered_relation_facets(reasoning_input) for item in facet.brands])


def _relation_platforms(reasoning_input: FashionReasoningInput) -> list[str]:
    return _dedupe(
        [item for facet in _ordered_relation_facets(reasoning_input) for item in facet.platforms]
    )


def _overlap_contexts(reasoning_input: FashionReasoningInput) -> list[str]:
    return _dedupe(
        [item for facet in _ordered_advice_facets(reasoning_input) for item in facet.overlap_context]
    )


def _ordered_advice_facets(reasoning_input: FashionReasoningInput):
    return _ordered_facets(reasoning_input.style_advice_facets, reasoning_input, "advice")


def _ordered_image_facets(reasoning_input: FashionReasoningInput):
    return _ordered_facets(reasoning_input.style_image_facets, reasoning_input, "image")


def _ordered_visual_language_facets(reasoning_input: FashionReasoningInput):
    return _ordered_facets(reasoning_input.style_visual_language_facets, reasoning_input, "visual")


def _ordered_relation_facets(reasoning_input: FashionReasoningInput):
    return _ordered_facets(reasoning_input.style_relation_facets, reasoning_input, "relation")


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


_FOOTWEAR_TERMS = (
    "boot",
    "boots",
    "loafer",
    "loafers",
    "sneaker",
    "sneakers",
    "shoe",
    "shoes",
    "heel",
    "heels",
    "sandal",
    "sandals",
    "pump",
    "pumps",
    "mule",
    "mules",
    "flat",
    "flats",
    "oxford",
    "oxfords",
    "derby",
    "derbies",
    "mary jane",
)

_ACCESSORY_TERMS = (
    "bag",
    "belt",
    "brooch",
    "cap",
    "clutch",
    "earring",
    "glasses",
    "glove",
    "hat",
    "headband",
    "headphones",
    "jewelry",
    "necklace",
    "ring",
    "scarf",
    "sunglasses",
    "tie",
    "watch",
)

_MATERIAL_TERMS = (
    "cotton",
    "denim",
    "leather",
    "linen",
    "mesh",
    "nylon",
    "satin",
    "silk",
    "suede",
    "tulle",
    "tweed",
    "velvet",
    "wool",
)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result
