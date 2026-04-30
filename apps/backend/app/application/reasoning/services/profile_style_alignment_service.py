from collections.abc import Iterable
from typing import Any

from app.domain.reasoning import (
    ProfileAlignedStyleFacetBundle,
    ProfileContextSnapshot,
    StyleAdviceFacet,
    StyleFacetBundle,
    StyleImageFacet,
    StyleRelationFacet,
    StyleVisualLanguageFacet,
)


class DefaultProfileStyleAlignmentService:
    async def align(
        self,
        *,
        profile: ProfileContextSnapshot,
        style_facets: StyleFacetBundle,
    ) -> ProfileAlignedStyleFacetBundle:
        aligned_facets = style_facets.model_copy(deep=True)
        notes: list[str] = []
        filtered_out: list[str] = []
        boosted_categories: list[str] = []
        removed_item_types: list[str] = []

        if not profile.present or not profile.values:
            return ProfileAlignedStyleFacetBundle(
                facets=aligned_facets,
                profile_context_present=profile.present,
                alignment_notes=["profile context is absent or empty"],
                boosted_facet_categories=[],
                removed_item_types=[],
                facet_weights=_facet_weights(
                    facets=aligned_facets,
                    preference_terms=[],
                    avoidance_terms=[],
                ),
            )

        values = profile.values
        blocked_terms = _profile_terms(
            values,
            (
                "avoid_hero_garments",
                "avoid_garments",
                "excluded_garments",
                "unavailable_garments",
                "forbidden_garments",
                "avoided_items",
                "avoid_items",
                "avoided_garments",
            ),
        )
        preferred_item_terms = _profile_terms(
            values,
            (
                "preferred_items",
                "favorite_items",
                "preferred_garments",
                "wardrobe_items",
            ),
        )
        silhouette_terms = _profile_terms(
            values,
            (
                "preferred_silhouette",
                "silhouette_preferences",
                "silhouette",
                "fit",
                "fit_preference",
                "fit_preferences",
                "body_fit_preference",
            ),
        )
        comfort_terms = _profile_terms(
            values,
            (
                "comfort",
                "comfort_preference",
                "comfort_preferences",
                "mobility_preference",
            ),
        )
        formality_terms = _profile_terms(
            values,
            (
                "formality",
                "formality_preference",
                "formality_preferences",
                "occasion_formality",
                "dress_code",
            ),
        )
        palette_terms = _profile_terms(
            values,
            (
                "preferred_colors",
                "preferred_palette",
                "palette",
                "color_preference",
                "color_preferences",
            ),
        )
        color_avoidance_terms = _profile_terms(
            values,
            (
                "avoid_colors",
                "avoided_colors",
                "color_avoidances",
                "palette_avoidances",
            ),
        )
        relation_preference_terms = _profile_terms(
            values,
            (
                "presentation_profile",
                "style_preferences",
                "preferred_styles",
                "preferred_brands",
                "preferred_platforms",
            ),
        )
        relation_avoidance_terms = _profile_terms(
            values,
            (
                "style_avoidances",
                "avoided_styles",
                "avoid_styles",
                "avoided_brands",
                "avoided_platforms",
            ),
        )
        presentation_preference_terms = _presentation_preference_terms(
            values.get("presentation_profile")
        )
        presentation_penalty_terms = _presentation_penalty_terms(values.get("presentation_profile"))
        silhouette_penalty_terms = _silhouette_penalty_terms(silhouette_terms)
        comfort_penalty_terms = _comfort_penalty_terms(comfort_terms)
        formality_penalty_terms = _formality_penalty_terms(formality_terms)
        wearability_triggered = _wearability_triggered(
            comfort_terms=comfort_terms,
            formality_terms=formality_terms,
        )

        if blocked_terms:
            aligned_facets.image_facets = [
                _filter_image_facet(facet, blocked_terms, filtered_out)
                for facet in aligned_facets.image_facets
            ]
            aligned_facets.advice_facets = [
                _filter_advice_facet(facet, blocked_terms, filtered_out)
                for facet in aligned_facets.advice_facets
            ]
            notes.append("filtered garment and accessory cues that conflict with profile exclusions")
            removed_item_types.append("garments_and_accessories")

        if preferred_item_terms:
            aligned_facets.image_facets = [
                _prioritize_image_items(facet, preferred_item_terms)
                for facet in aligned_facets.image_facets
            ]
            aligned_facets.advice_facets = [
                _prioritize_advice_items(facet, preferred_item_terms)
                for facet in aligned_facets.advice_facets
            ]
            notes.append("boosted preferred wardrobe items across advice and image facets")
            boosted_categories.extend(["advice", "image"])

        if presentation_preference_terms:
            aligned_facets.advice_facets = [
                _prioritize_advice_facet(facet, presentation_preference_terms)
                for facet in aligned_facets.advice_facets
            ]
            aligned_facets.image_facets = [
                _prioritize_image_facet(facet, presentation_preference_terms)
                for facet in aligned_facets.image_facets
            ]
            aligned_facets.relation_facets = [
                _prioritize_relation_facet(facet, presentation_preference_terms)
                for facet in aligned_facets.relation_facets
            ]
            notes.append("boosted presentation-relevant cues across aligned facets")
            boosted_categories.extend(["advice", "image", "relation"])

        if silhouette_terms or comfort_terms:
            fit_terms = _unique_terms([*silhouette_terms, *comfort_terms])
            aligned_facets.advice_facets = [
                _prioritize_advice_facet(facet, fit_terms)
                for facet in aligned_facets.advice_facets
            ]
            aligned_facets.image_facets = [
                _prioritize_image_facet(facet, fit_terms)
                for facet in aligned_facets.image_facets
            ]
            notes.append("prioritized silhouette-relevant styling and composition cues")
            boosted_categories.extend(["advice", "image"])

        if formality_terms:
            aligned_facets.advice_facets = [
                _prioritize_formality(facet, formality_terms)
                for facet in aligned_facets.advice_facets
            ]
            notes.append("prioritized advice variants matching profile formality signals")
            boosted_categories.append("advice")

        if color_avoidance_terms:
            aligned_facets.visual_language_facets = [
                _filter_visual_language_facet(facet, color_avoidance_terms, filtered_out)
                for facet in aligned_facets.visual_language_facets
            ]
            notes.append("filtered visual-language palette cues that conflict with profile color avoidances")
            removed_item_types.append("palette")

        if palette_terms:
            aligned_facets.visual_language_facets = [
                _prioritize_visual_language_facet(facet, palette_terms)
                for facet in aligned_facets.visual_language_facets
            ]
            notes.append("prioritized visual-language palette cues matching profile preferences")
            boosted_categories.append("visual_language")

        if relation_avoidance_terms:
            aligned_facets.relation_facets = [
                _filter_relation_facet(facet, relation_avoidance_terms, filtered_out)
                for facet in aligned_facets.relation_facets
            ]
            notes.append("filtered relation cues that conflict with profile style or brand avoidances")
            removed_item_types.append("relation")

        if relation_preference_terms:
            aligned_facets.relation_facets = [
                _prioritize_relation_facet(facet, relation_preference_terms)
                for facet in aligned_facets.relation_facets
            ]
            notes.append("prioritized relation cues matching profile style, brand, or platform preferences")
            boosted_categories.append("relation")

        penalty_terms = _unique_terms(
            [
                *presentation_penalty_terms,
                *silhouette_penalty_terms,
                *comfort_penalty_terms,
                *formality_penalty_terms,
            ]
        )
        if penalty_terms:
            aligned_facets.advice_facets = [
                _demote_advice_facet(facet, penalty_terms)
                for facet in aligned_facets.advice_facets
            ]
            aligned_facets.image_facets = [
                _demote_image_facet(facet, penalty_terms)
                for facet in aligned_facets.image_facets
            ]
            aligned_facets.visual_language_facets = [
                _demote_visual_language_facet(facet, penalty_terms)
                for facet in aligned_facets.visual_language_facets
            ]
            notes.append("softly de-emphasized cues that conflict with profile silhouette, comfort, or presentation")

        if wearability_triggered:
            aligned_facets.advice_facets = [
                _soften_editorial_emphasis(facet)
                for facet in aligned_facets.advice_facets
            ]
            aligned_facets.image_facets = [
                _soften_editorial_image_emphasis(facet)
                for facet in aligned_facets.image_facets
            ]
            notes.append("softened editorial emphasis toward more wearable profile-aligned adaptations")
            boosted_categories.extend(["advice", "image"])

        if not notes:
            notes.append("profile context present; no explicit facet adjustments were needed")

        preference_terms = _unique_terms(
            [
                *preferred_item_terms,
                *presentation_preference_terms,
                *silhouette_terms,
                *comfort_terms,
                *formality_terms,
                *palette_terms,
                *relation_preference_terms,
            ]
        )
        avoidance_terms = _unique_terms(
            [
                *blocked_terms,
                *color_avoidance_terms,
                *relation_avoidance_terms,
                *penalty_terms,
            ]
        )
        facet_weights = _facet_weights(
            facets=aligned_facets,
            preference_terms=preference_terms,
            avoidance_terms=avoidance_terms,
        )
        if facet_weights:
            notes.append("computed profile facet weights for downstream ranking")

        return ProfileAlignedStyleFacetBundle(
            facets=aligned_facets,
            profile_context_present=True,
            alignment_notes=notes,
            filtered_out=filtered_out,
            boosted_facet_categories=_unique_terms(boosted_categories),
            removed_item_types=_unique_terms(removed_item_types),
            facet_weights=facet_weights,
        )


def _profile_terms(values: dict[str, Any], keys: Iterable[str]) -> list[str]:
    terms: list[str] = []
    for key in keys:
        value = values.get(key)
        terms.extend(_flatten_terms(value))
    return _unique_terms(terms)


def _flatten_terms(value: Any) -> list[str]:
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, str):
        return [part.strip().lower() for part in value.replace(";", ",").split(",") if part.strip()]
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, dict)):
        terms: list[str] = []
        for item in value:
            terms.extend(_flatten_terms(item))
        return terms
    return [str(value).strip().lower()] if str(value).strip() else []


def _unique_terms(terms: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for term in terms:
        normalized = term.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _filter_image_facet(
    facet: StyleImageFacet,
    blocked_terms: list[str],
    filtered_out: list[str],
) -> StyleImageFacet:
    updated = facet.model_copy(deep=True)
    for field_name in ("hero_garments", "secondary_garments", "core_accessories", "props"):
        setattr(updated, field_name, _without_blocked(getattr(updated, field_name), blocked_terms, filtered_out))
    return updated


def _filter_advice_facet(
    facet: StyleAdviceFacet,
    blocked_terms: list[str],
    filtered_out: list[str],
) -> StyleAdviceFacet:
    updated = facet.model_copy(deep=True)
    updated.statement_pieces = _without_blocked(updated.statement_pieces, blocked_terms, filtered_out)
    return updated


def _filter_visual_language_facet(
    facet: StyleVisualLanguageFacet,
    blocked_terms: list[str],
    filtered_out: list[str],
) -> StyleVisualLanguageFacet:
    updated = facet.model_copy(deep=True)
    updated.palette = _without_blocked(updated.palette, blocked_terms, filtered_out)
    updated.mood_keywords = _without_blocked(updated.mood_keywords, blocked_terms, filtered_out)
    return updated


def _filter_relation_facet(
    facet: StyleRelationFacet,
    blocked_terms: list[str],
    filtered_out: list[str],
) -> StyleRelationFacet:
    updated = facet.model_copy(deep=True)
    for field_name in ("related_styles", "overlap_styles", "historical_relations", "brands", "platforms"):
        setattr(updated, field_name, _without_blocked(getattr(updated, field_name), blocked_terms, filtered_out))
    return updated


def _without_blocked(items: list[str], blocked_terms: list[str], filtered_out: list[str]) -> list[str]:
    kept: list[str] = []
    for item in items:
        if _matches_any(item, blocked_terms):
            filtered_out.append(item)
        else:
            kept.append(item)
    return kept


def _prioritize_advice_facet(facet: StyleAdviceFacet, terms: list[str]) -> StyleAdviceFacet:
    updated = facet.model_copy(deep=True)
    updated.core_style_logic = _prioritize_items(updated.core_style_logic, terms)
    updated.styling_rules = _prioritize_items(updated.styling_rules, terms)
    updated.casual_adaptations = _prioritize_items(updated.casual_adaptations, terms)
    return updated


def _prioritize_image_facet(facet: StyleImageFacet, terms: list[str]) -> StyleImageFacet:
    updated = facet.model_copy(deep=True)
    updated.hero_garments = _prioritize_items(updated.hero_garments, terms)
    updated.secondary_garments = _prioritize_items(updated.secondary_garments, terms)
    updated.core_accessories = _prioritize_items(updated.core_accessories, terms)
    updated.props = _prioritize_items(updated.props, terms)
    updated.composition_cues = _prioritize_items(updated.composition_cues, terms)
    return updated


def _prioritize_image_items(facet: StyleImageFacet, terms: list[str]) -> StyleImageFacet:
    updated = facet.model_copy(deep=True)
    updated.hero_garments = _prioritize_items(updated.hero_garments, terms)
    updated.secondary_garments = _prioritize_items(updated.secondary_garments, terms)
    updated.core_accessories = _prioritize_items(updated.core_accessories, terms)
    updated.props = _prioritize_items(updated.props, terms)
    return updated


def _prioritize_advice_items(facet: StyleAdviceFacet, terms: list[str]) -> StyleAdviceFacet:
    updated = facet.model_copy(deep=True)
    updated.statement_pieces = _prioritize_items(updated.statement_pieces, terms)
    updated.styling_rules = _prioritize_items(updated.styling_rules, terms)
    return updated


def _prioritize_formality(facet: StyleAdviceFacet, terms: list[str]) -> StyleAdviceFacet:
    updated = facet.model_copy(deep=True)
    if any(term in {"casual", "relaxed", "everyday"} for term in terms):
        updated.casual_adaptations = _prioritize_items(updated.casual_adaptations, terms)
        updated.styling_rules = _dedupe([*updated.casual_adaptations, *updated.styling_rules])
    elif any(term in {"formal", "dressy", "evening", "office", "business"} for term in terms):
        updated.status_markers = _prioritize_items(updated.status_markers, terms)
        updated.styling_rules = _dedupe([*updated.status_markers, *updated.styling_rules])
    return updated


def _prioritize_visual_language_facet(
    facet: StyleVisualLanguageFacet,
    terms: list[str],
) -> StyleVisualLanguageFacet:
    updated = facet.model_copy(deep=True)
    updated.palette = _prioritize_items(updated.palette, terms)
    updated.mood_keywords = _prioritize_items(updated.mood_keywords, terms)
    updated.visual_motifs = _prioritize_items(updated.visual_motifs, terms)
    updated.platform_visual_cues = _prioritize_items(updated.platform_visual_cues, terms)
    return updated


def _prioritize_relation_facet(
    facet: StyleRelationFacet,
    terms: list[str],
) -> StyleRelationFacet:
    updated = facet.model_copy(deep=True)
    updated.related_styles = _prioritize_items(updated.related_styles, terms)
    updated.overlap_styles = _prioritize_items(updated.overlap_styles, terms)
    updated.historical_relations = _prioritize_items(updated.historical_relations, terms)
    updated.brands = _prioritize_items(updated.brands, terms)
    updated.platforms = _prioritize_items(updated.platforms, terms)
    return updated


def _prioritize_items(items: list[str], terms: list[str]) -> list[str]:
    matching = [item for item in items if _matches_any(item, terms)]
    rest = [item for item in items if not _matches_any(item, terms)]
    return [*_dedupe(matching), *_dedupe(rest)]


def _demote_items(items: list[str], terms: list[str]) -> list[str]:
    kept = [item for item in items if not _matches_any(item, terms)]
    demoted = [item for item in items if _matches_any(item, terms)]
    return [*_dedupe(kept), *_dedupe(demoted)]


def _demote_advice_facet(facet: StyleAdviceFacet, terms: list[str]) -> StyleAdviceFacet:
    updated = facet.model_copy(deep=True)
    updated.core_style_logic = _demote_items(updated.core_style_logic, terms)
    updated.styling_rules = _demote_items(updated.styling_rules, terms)
    updated.statement_pieces = _demote_items(updated.statement_pieces, terms)
    updated.status_markers = _demote_items(updated.status_markers, terms)
    return updated


def _demote_image_facet(facet: StyleImageFacet, terms: list[str]) -> StyleImageFacet:
    updated = facet.model_copy(deep=True)
    updated.hero_garments = _demote_items(updated.hero_garments, terms)
    updated.secondary_garments = _demote_items(updated.secondary_garments, terms)
    updated.core_accessories = _demote_items(updated.core_accessories, terms)
    updated.props = _demote_items(updated.props, terms)
    updated.composition_cues = _demote_items(updated.composition_cues, terms)
    return updated


def _demote_visual_language_facet(
    facet: StyleVisualLanguageFacet,
    terms: list[str],
) -> StyleVisualLanguageFacet:
    updated = facet.model_copy(deep=True)
    updated.mood_keywords = _demote_items(updated.mood_keywords, terms)
    updated.visual_motifs = _demote_items(updated.visual_motifs, terms)
    updated.platform_visual_cues = _demote_items(updated.platform_visual_cues, terms)
    return updated


def _soften_editorial_emphasis(facet: StyleAdviceFacet) -> StyleAdviceFacet:
    updated = facet.model_copy(deep=True)
    editorial_terms = _editorial_penalty_terms()
    if updated.casual_adaptations:
        updated.styling_rules = _dedupe([*updated.casual_adaptations, *updated.styling_rules])
    updated.statement_pieces = _demote_items(updated.statement_pieces, editorial_terms)
    updated.status_markers = _demote_items(updated.status_markers, editorial_terms)
    updated.styling_rules = _demote_items(updated.styling_rules, editorial_terms)
    return updated


def _soften_editorial_image_emphasis(facet: StyleImageFacet) -> StyleImageFacet:
    updated = facet.model_copy(deep=True)
    editorial_terms = _editorial_penalty_terms()
    updated.hero_garments = _demote_items(updated.hero_garments, editorial_terms)
    updated.secondary_garments = _demote_items(updated.secondary_garments, editorial_terms)
    updated.core_accessories = _demote_items(updated.core_accessories, editorial_terms)
    updated.props = _demote_items(updated.props, editorial_terms)
    updated.composition_cues = _demote_items(updated.composition_cues, editorial_terms)
    return updated


def _matches_any(value: str, terms: list[str]) -> bool:
    normalized = value.lower()
    return any(term in normalized for term in terms)


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _facet_weights(
    *,
    facets: StyleFacetBundle,
    preference_terms: list[str],
    avoidance_terms: list[str],
) -> dict[str, float]:
    weights: dict[str, float] = {}
    for facet in facets.advice_facets:
        weights[f"advice:{facet.style_id}"] = _weight_for_texts(
            _facet_texts(facet),
            preference_terms=preference_terms,
            avoidance_terms=avoidance_terms,
        )
    for facet in facets.image_facets:
        weights[f"image:{facet.style_id}"] = _weight_for_texts(
            _facet_texts(facet),
            preference_terms=preference_terms,
            avoidance_terms=avoidance_terms,
        )
    for facet in facets.visual_language_facets:
        weights[f"visual:{facet.style_id}"] = _weight_for_texts(
            _facet_texts(facet),
            preference_terms=preference_terms,
            avoidance_terms=avoidance_terms,
        )
    for facet in facets.relation_facets:
        weights[f"relation:{facet.style_id}"] = _weight_for_texts(
            _facet_texts(facet),
            preference_terms=preference_terms,
            avoidance_terms=avoidance_terms,
        )
    return weights


def _weight_for_texts(
    texts: list[str],
    *,
    preference_terms: list[str],
    avoidance_terms: list[str],
) -> float:
    score = 1.0
    if preference_terms and any(_matches_any(text, preference_terms) for text in texts):
        score += 0.25
    if avoidance_terms and any(_matches_any(text, avoidance_terms) for text in texts):
        score -= 0.35
    return max(0.25, min(1.5, round(score, 2)))


def _facet_texts(facet: Any) -> list[str]:
    values: list[str] = []
    for value in facet.model_dump(mode="python").values():
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, dict)):
            values.extend(str(item) for item in value)
    return values


def _presentation_preference_terms(value: Any) -> list[str]:
    normalized = _flatten_terms(value)
    if not normalized:
        return []
    profile = normalized[0]
    mapping = {
        "feminine": ["soft", "fluid", "dress", "skirt", "heel", "romantic", "delicate"],
        "masculine": ["tailored", "structured", "sharp", "straight", "boot", "loafer", "trouser"],
        "androgynous": ["structured", "clean", "tailored", "minimal", "straight", "blazer", "loafer"],
        "unisex": ["clean", "minimal", "balanced", "neutral", "straight", "tailored"],
    }
    return mapping.get(profile, [])


def _presentation_penalty_terms(value: Any) -> list[str]:
    normalized = _flatten_terms(value)
    if not normalized:
        return []
    profile = normalized[0]
    mapping = {
        "masculine": ["frill", "ruffle", "bow", "ornate"],
        "androgynous": ["frill", "ruffle", "ornate", "princess", "glitter", "hyper-decorative"],
        "unisex": ["frill", "ruffle", "ornate", "princess", "hyper-decorative"],
    }
    return mapping.get(profile, [])


def _silhouette_penalty_terms(terms: list[str]) -> list[str]:
    penalties: list[str] = []
    if any(term == "structured" for term in terms):
        penalties.extend(["soft", "romantic", "ruffle", "frill", "slouchy"])
    if any(term == "soft" for term in terms):
        penalties.extend(["sharp", "rigid", "angular", "tailored"])
    if any(term == "elongated" for term in terms):
        penalties.extend(["cropped", "boxy"])
    if any(term == "minimal" for term in terms):
        penalties.extend(["ornate", "maximal", "busy", "decorative"])
    if any(term == "relaxed" for term in terms):
        penalties.extend(["corset", "bodycon", "tight", "fitted"])
    if any(term == "fitted" for term in terms):
        penalties.extend(["oversized", "slouchy", "boxy"])
    if any(term == "oversized" for term in terms):
        penalties.extend(["bodycon", "tight", "tailored"])
    return _unique_terms(penalties)


def _comfort_penalty_terms(terms: list[str]) -> list[str]:
    penalties: list[str] = []
    if "high_comfort" in terms:
        penalties.extend(["heel", "stiletto", "corset", "fragile", "delicate", "dry clean", "tight"])
    elif "balanced" in terms:
        penalties.extend(["stiletto", "corset"])
    return _unique_terms(penalties)


def _formality_penalty_terms(terms: list[str]) -> list[str]:
    penalties: list[str] = []
    if "casual" in terms:
        penalties.extend(["gown", "black tie", "ceremonial", "evening glove"])
    if "smart_casual" in terms:
        penalties.extend(["gown", "black tie", "ceremonial", "stiletto"])
    if "refined" in terms:
        penalties.extend(["hoodie", "graphic tee", "distressed"])
    if "formal" in terms:
        penalties.extend(["hoodie", "graphic tee", "distressed", "sneaker"])
    return _unique_terms(penalties)


def _wearability_triggered(*, comfort_terms: list[str], formality_terms: list[str]) -> bool:
    return "high_comfort" in comfort_terms or any(
        term in {"casual", "smart_casual"} for term in formality_terms
    )


def _editorial_penalty_terms() -> list[str]:
    return [
        "editorial",
        "runway",
        "couture",
        "fragile",
        "high-maintenance",
        "feather",
        "stiletto",
        "heel",
        "corset",
        "ornate",
        "decorative",
    ]
