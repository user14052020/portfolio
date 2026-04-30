from app.domain.reasoning import (
    ProfileClarificationDecision,
    ProfileContextSnapshot,
    StyleFacetBundle,
)


class DefaultProfileClarificationPolicy:
    async def evaluate(
        self,
        *,
        mode: str,
        profile: ProfileContextSnapshot | None,
        style_bundle: StyleFacetBundle | None,
    ) -> ProfileClarificationDecision:
        if mode == "occasion_outfit" and not _has_silhouette_preference(profile):
            return ProfileClarificationDecision(
                should_ask=True,
                question_text="Do you prefer a relaxed, fitted, or oversized silhouette for this look?",
                missing_priority_fields=["silhouette_preferences"],
            )
        if (
            mode == "style_exploration"
            and _has_silhouette_preference(profile)
            and not _has_presentation_profile(profile)
        ):
            return ProfileClarificationDecision(
                should_ask=True,
                question_text=(
                    "Which presentation direction should guide this look: "
                    "feminine, masculine, androgynous, or universal?"
                ),
                missing_priority_fields=["presentation_profile"],
            )
        if (
            mode == "style_exploration"
            and _has_partial_profile_context(profile)
            and not _has_wearability_preference(profile)
            and _has_wearability_branching(style_bundle)
        ):
            return ProfileClarificationDecision(
                should_ask=True,
                question_text=(
                    "Do you want this to stay highly wearable, balanced, "
                    "or a bit more expressive?"
                ),
                missing_priority_fields=["comfort_preferences"],
            )
        return ProfileClarificationDecision(
            should_ask=False,
            question_text=None,
            missing_priority_fields=[],
        )


def _has_silhouette_preference(profile: ProfileContextSnapshot | None) -> bool:
    if profile is None or not profile.present:
        return False
    return bool(profile.silhouette_preferences or profile.fit_preferences)


def _has_presentation_profile(profile: ProfileContextSnapshot | None) -> bool:
    if profile is None or not profile.present:
        return False
    return bool(profile.presentation_profile)


def _has_wearability_preference(profile: ProfileContextSnapshot | None) -> bool:
    if profile is None or not profile.present:
        return False
    return bool(profile.comfort_preferences or profile.formality_preferences)


def _has_partial_profile_context(profile: ProfileContextSnapshot | None) -> bool:
    if profile is None or not profile.present:
        return False
    return bool(
        profile.presentation_profile
        or profile.fit_preferences
        or profile.silhouette_preferences
        or profile.color_preferences
        or profile.preferred_items
        or profile.avoided_items
    )


def _has_wearability_branching(style_bundle: StyleFacetBundle | None) -> bool:
    if style_bundle is None:
        return False
    has_casual_adaptations = any(facet.casual_adaptations for facet in style_bundle.advice_facets)
    has_expressive_cues = any(
        facet.statement_pieces or facet.status_markers
        for facet in style_bundle.advice_facets
    )
    return has_casual_adaptations and has_expressive_cues
