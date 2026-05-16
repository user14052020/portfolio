from collections.abc import Iterable
from typing import Any

from app.application.reasoning.profile_context_models import ProfileContextUpdate
from app.domain.reasoning import (
    PresentationProfile,
    ProfileContext,
    ProfileContextSnapshot,
)


class DefaultProfileContextNormalizer:
    _MAX_CATEGORICAL_ITEMS = 4
    _MAX_OPEN_TEXT_ITEMS = 8

    def normalize(
        self,
        profile: ProfileContext | ProfileContextSnapshot | ProfileContextUpdate | dict[str, Any] | None,
    ) -> ProfileContext:
        payload = _profile_payload(profile)
        return ProfileContext(
            presentation_profile=_normalize_presentation_profile(payload),
            fit_preferences=_normalize_closed_set(
                payload,
                keys=("fit_preferences", "fit", "fit_preference", "preferred_fit"),
                allowed={"fitted", "relaxed", "oversized", "balanced"},
                aliases={
                    "tailored": "fitted",
                    "slim": "fitted",
                    "close_fit": "fitted",
                    "loose": "relaxed",
                    "roomy": "relaxed",
                    "oversize": "oversized",
                    "regular": "balanced",
                },
                max_items=self._MAX_CATEGORICAL_ITEMS,
            ),
            silhouette_preferences=_normalize_closed_set(
                payload,
                keys=(
                    "silhouette_preferences",
                    "preferred_silhouette",
                    "silhouette",
                    "silhouettes",
                ),
                allowed={
                    "elongated",
                    "soft",
                    "structured",
                    "minimal",
                    "layered",
                    "voluminous_top",
                    "balanced_proportions",
                },
                aliases={
                    "balance": "balanced_proportions",
                    "balanced": "balanced_proportions",
                    "balanced proportions": "balanced_proportions",
                    "voluminous top": "voluminous_top",
                },
                max_items=self._MAX_CATEGORICAL_ITEMS,
            ),
            comfort_preferences=_normalize_closed_set(
                payload,
                keys=("comfort_preferences", "comfort_preference", "comfort", "mobility_preference"),
                allowed={"high_comfort", "balanced", "style_first"},
                aliases={
                    "comfortable": "high_comfort",
                    "comfort_first": "high_comfort",
                    "style first": "style_first",
                    "style-first": "style_first",
                },
                max_items=self._MAX_CATEGORICAL_ITEMS,
            ),
            formality_preferences=_normalize_closed_set(
                payload,
                keys=(
                    "formality_preferences",
                    "formality_preference",
                    "formality",
                    "occasion_formality",
                    "dress_code",
                ),
                allowed={"casual", "smart_casual", "refined", "formal"},
                aliases={
                    "smart casual": "smart_casual",
                    "smart-casual": "smart_casual",
                    "polished": "refined",
                    "elevated": "refined",
                    "dressy": "formal",
                },
                max_items=self._MAX_CATEGORICAL_ITEMS,
            ),
            color_preferences=_normalize_open_text_set(
                payload,
                keys=("color_preferences", "color_preference", "preferred_colors", "preferred_palette", "palette"),
                max_items=self._MAX_OPEN_TEXT_ITEMS,
            ),
            color_avoidances=_normalize_open_text_set(
                payload,
                keys=("color_avoidances", "avoid_colors", "avoided_colors", "palette_avoidances"),
                max_items=self._MAX_OPEN_TEXT_ITEMS,
            ),
            preferred_items=_normalize_open_text_set(
                payload,
                keys=("preferred_items", "favorite_items", "preferred_garments", "wardrobe_items"),
                max_items=self._MAX_OPEN_TEXT_ITEMS,
            ),
            avoided_items=_normalize_open_text_set(
                payload,
                keys=(
                    "avoided_items",
                    "avoid_items",
                    "avoided_garments",
                    "avoid_garments",
                    "avoid_hero_garments",
                    "excluded_garments",
                    "unavailable_garments",
                    "forbidden_garments",
                ),
                max_items=self._MAX_OPEN_TEXT_ITEMS,
            ),
        )

    def snapshot(
        self,
        profile: ProfileContext | ProfileContextSnapshot | ProfileContextUpdate | dict[str, Any] | None,
        *,
        source: str = "runtime",
    ) -> ProfileContextSnapshot:
        payload = _profile_payload(profile)
        return self.normalize(profile).snapshot(
            source=source,
            legacy_values=_legacy_passthrough_values(payload),
        )


def _profile_payload(
    profile: ProfileContext | ProfileContextSnapshot | ProfileContextUpdate | dict[str, Any] | None,
) -> dict[str, Any]:
    if profile is None:
        return {}
    if isinstance(profile, ProfileContext):
        return profile.model_dump()
    if isinstance(profile, ProfileContextSnapshot):
        return profile.values
    if isinstance(profile, ProfileContextUpdate):
        return profile.model_dump(exclude_none=True)
    if isinstance(profile, dict):
        return dict(profile)
    return {}


_KNOWN_PROFILE_INPUT_KEYS = {
    "presentation_profile",
    "gender",
    "fit_preferences",
    "fit",
    "fit_preference",
    "preferred_fit",
    "silhouette_preferences",
    "preferred_silhouette",
    "silhouette",
    "silhouettes",
    "comfort_preferences",
    "comfort_preference",
    "comfort",
    "mobility_preference",
    "formality_preferences",
    "formality_preference",
    "formality",
    "occasion_formality",
    "dress_code",
    "color_preferences",
    "color_preference",
    "preferred_colors",
    "preferred_palette",
    "palette",
    "color_avoidances",
    "avoid_colors",
    "avoided_colors",
    "palette_avoidances",
    "preferred_items",
    "favorite_items",
    "preferred_garments",
    "wardrobe_items",
    "avoided_items",
    "avoid_items",
    "avoided_garments",
    "avoid_garments",
    "avoid_hero_garments",
    "excluded_garments",
    "unavailable_garments",
    "forbidden_garments",
    "source",
    "present",
    "values",
    "legacy_values",
}


def _legacy_passthrough_values(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in _KNOWN_PROFILE_INPUT_KEYS and value is not None
    }


def _normalize_presentation_profile(payload: dict[str, Any]) -> PresentationProfile | None:
    raw_value = payload.get("presentation_profile", payload.get("gender"))
    if isinstance(raw_value, PresentationProfile):
        return raw_value
    normalized = _normalize_categorical_term(raw_value)
    mapping = {
        "feminine": PresentationProfile.FEMININE,
        "female": PresentationProfile.FEMININE,
        "woman": PresentationProfile.FEMININE,
        "masculine": PresentationProfile.MASCULINE,
        "male": PresentationProfile.MASCULINE,
        "man": PresentationProfile.MASCULINE,
        "androgynous": PresentationProfile.ANDROGYNOUS,
        "neutral": PresentationProfile.UNISEX,
        "universal": PresentationProfile.UNISEX,
        "unisex": PresentationProfile.UNISEX,
    }
    return mapping.get(normalized)


def _normalize_closed_set(
    payload: dict[str, Any],
    *,
    keys: tuple[str, ...],
    allowed: set[str],
    aliases: dict[str, str],
    max_items: int,
) -> list[str]:
    normalized: list[str] = []
    for raw_value in _collect_terms(payload, keys, normalizer=_normalize_categorical_term):
        token = aliases.get(raw_value, raw_value)
        if token in allowed and token not in normalized:
            normalized.append(token)
        if len(normalized) >= max_items:
            break
    return normalized


def _normalize_open_text_set(
    payload: dict[str, Any],
    *,
    keys: tuple[str, ...],
    max_items: int,
) -> list[str]:
    normalized: list[str] = []
    for raw_value in _collect_terms(payload, keys, normalizer=_normalize_text_term):
        if raw_value not in normalized:
            normalized.append(raw_value)
        if len(normalized) >= max_items:
            break
    return normalized


def _collect_terms(
    payload: dict[str, Any],
    keys: tuple[str, ...],
    *,
    normalizer,
) -> list[str]:
    collected: list[str] = []
    for key in keys:
        collected.extend(_flatten_terms(payload.get(key), normalizer=normalizer))
    return collected


def _flatten_terms(value: Any, *, normalizer) -> list[str]:
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, str):
        return [term for term in (normalizer(part) for part in value.replace(";", ",").split(",")) if term]
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, dict)):
        flattened: list[str] = []
        for item in value:
            flattened.extend(_flatten_terms(item, normalizer=normalizer))
        return flattened
    term = normalizer(value)
    return [term] if term else []


def _normalize_categorical_term(value: Any) -> str:
    text = str(value).strip().lower()
    return text.replace("-", "_").replace(" ", "_") if text else ""


def _normalize_text_term(value: Any) -> str:
    text = " ".join(str(value).strip().lower().split())
    return text
