from app.domain.reasoning import (
    ProfileClarificationDecision,
    ProfileContextSnapshot,
    StyleFacetBundle,
)


class ProfileClarificationQuestionCatalog:
    _QUESTIONS = {
        "occasion_silhouette": {
            "en": "Do you prefer a relaxed, fitted, or oversized silhouette for this look?",
            "ru": "Вам ближе расслабленный, приталенный или оверсайз-силуэт для этого образа?",
        },
        "style_presentation": {
            "en": "Which presentation direction should guide this look: feminine, masculine, androgynous, or universal?",
            "ru": "Какое направление образа взять за основу: женственное, мужское, андрогинное или универсальное?",
        },
        "style_wearability": {
            "en": "Do you want this to stay highly wearable, balanced, or a bit more expressive?",
            "ru": "Сделать стиль максимально носибельным, сбалансированным или более выразительным?",
        },
    }

    def text(self, question_key: str, locale: str) -> str:
        normalized_locale = "ru" if locale == "ru" else "en"
        question = self._QUESTIONS.get(question_key)
        if question is None:
            return (
                "Какую деталь учесть, чтобы точнее собрать направление?"
                if normalized_locale == "ru"
                else "What detail should I use to narrow this down?"
            )
        return question[normalized_locale]


class DefaultProfileClarificationPolicy:
    def __init__(
        self,
        *,
        question_catalog: ProfileClarificationQuestionCatalog | None = None,
    ) -> None:
        self._question_catalog = question_catalog or ProfileClarificationQuestionCatalog()

    async def evaluate(
        self,
        *,
        mode: str,
        profile: ProfileContextSnapshot | None,
        style_bundle: StyleFacetBundle | None,
        locale: str = "en",
    ) -> ProfileClarificationDecision:
        if mode == "occasion_outfit" and not _has_silhouette_preference(profile):
            return self._question(
                "occasion_silhouette",
                locale=locale,
                missing_priority_fields=["silhouette_preferences"],
            )
        if (
            mode == "style_exploration"
            and _has_silhouette_preference(profile)
            and not _has_presentation_profile(profile)
        ):
            return self._question(
                "style_presentation",
                locale=locale,
                missing_priority_fields=["presentation_profile"],
            )
        if (
            mode == "style_exploration"
            and _has_partial_profile_context(profile)
            and not _has_wearability_preference(profile)
            and _has_wearability_branching(style_bundle)
        ):
            return self._question(
                "style_wearability",
                locale=locale,
                missing_priority_fields=["comfort_preferences"],
            )
        return ProfileClarificationDecision(
            should_ask=False,
            question_text=None,
            missing_priority_fields=[],
        )

    def _question(
        self,
        question_key: str,
        *,
        locale: str,
        missing_priority_fields: list[str],
    ) -> ProfileClarificationDecision:
        return ProfileClarificationDecision(
            should_ask=True,
            question_key=question_key,
            question_text=self._question_catalog.text(question_key, locale),
            missing_priority_fields=missing_priority_fields,
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
