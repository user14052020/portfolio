from typing import Any

from app.application.reasoning.profile_context_models import ProfileContextInput, ProfileContextUpdate
from app.application.reasoning.services.profile_context_normalizer import DefaultProfileContextNormalizer
from app.domain.reasoning import ProfileContext, ProfileContextSnapshot


class DefaultProfileContextService:
    def __init__(
        self,
        *,
        normalizer: DefaultProfileContextNormalizer | None = None,
    ) -> None:
        self._normalizer = normalizer or DefaultProfileContextNormalizer()

    async def build_context(self, request: ProfileContextInput) -> ProfileContext:
        return self.build_context_sync(request)

    def build_context_sync(self, request: ProfileContextInput) -> ProfileContext:
        profile = self._normalizer.normalize(request.persistent_profile)
        profile = self.merge_updates_sync(
            current=profile,
            updates=self._update_from_source(request.session_profile),
        )
        profile = self.merge_updates_sync(
            current=profile,
            updates=self._update_from_source(request.frontend_hints),
        )
        profile = self.merge_updates_sync(
            current=profile,
            updates=self._update_from_source(request.recent_updates),
        )
        return profile

    async def build_snapshot(self, request: ProfileContextInput) -> ProfileContextSnapshot:
        return self.build_snapshot_sync(request)

    def build_snapshot_sync(self, request: ProfileContextInput) -> ProfileContextSnapshot:
        profile = self.build_context_sync(request)
        snapshot_payload = {
            **_passthrough_profile_payload(request.persistent_profile),
            **_passthrough_profile_payload(request.session_profile),
            **_passthrough_profile_payload(request.frontend_hints),
            **_passthrough_profile_payload(request.recent_updates),
            **profile.model_dump(),
        }
        return self._normalizer.snapshot(snapshot_payload, source="profile_context_service")

    async def merge_updates(
        self,
        current: ProfileContext,
        updates: ProfileContextUpdate,
    ) -> ProfileContext:
        return self.merge_updates_sync(current=current, updates=updates)

    def merge_updates_sync(
        self,
        *,
        current: ProfileContext,
        updates: ProfileContextUpdate,
    ) -> ProfileContext:
        current_payload = current.model_dump()
        update_payload = updates.model_dump(exclude_none=True)
        merged_payload: dict[str, Any] = dict(current_payload)
        merged_payload.update(update_payload)
        return self._normalizer.normalize(merged_payload)

    async def snapshot(
        self,
        profile: ProfileContext | ProfileContextSnapshot | dict[str, Any] | None,
    ) -> ProfileContextSnapshot:
        return self._normalizer.snapshot(profile, source="profile_context_service")

    async def completeness_state(
        self,
        profile: ProfileContext | ProfileContextSnapshot | dict[str, Any] | None,
    ) -> str:
        return self.completeness_state_sync(profile)

    def completeness_state_sync(
        self,
        profile: ProfileContext | ProfileContextSnapshot | dict[str, Any] | None,
    ) -> str:
        snapshot = (
            profile
            if isinstance(profile, ProfileContextSnapshot)
            else self._normalizer.snapshot(profile, source="profile_context_service")
        )
        if not snapshot.present:
            return "missing"
        important_signals = 0
        if snapshot.presentation_profile:
            important_signals += 1
        if snapshot.fit_preferences or snapshot.silhouette_preferences:
            important_signals += 1
        if snapshot.comfort_preferences or snapshot.formality_preferences:
            important_signals += 1
        if important_signals >= 3:
            return "strong"
        if important_signals >= 1:
            return "partial"
        return "missing"

    def _update_from_source(
        self,
        source: ProfileContext | ProfileContextSnapshot | dict[str, Any] | None,
    ) -> ProfileContextUpdate:
        normalized = self._normalizer.normalize(source)
        touched_fields = _touched_profile_fields(source)
        update_payload: dict[str, Any] = {}
        if "presentation_profile" in touched_fields:
            update_payload["presentation_profile"] = (
                normalized.presentation_profile.value
                if normalized.presentation_profile is not None
                else None
            )
        list_fields = {
            "fit_preferences": normalized.fit_preferences,
            "silhouette_preferences": normalized.silhouette_preferences,
            "comfort_preferences": normalized.comfort_preferences,
            "formality_preferences": normalized.formality_preferences,
            "color_preferences": normalized.color_preferences,
            "color_avoidances": normalized.color_avoidances,
            "preferred_items": normalized.preferred_items,
            "avoided_items": normalized.avoided_items,
        }
        for field_name, values in list_fields.items():
            if field_name in touched_fields:
                update_payload[field_name] = list(values)
        return ProfileContextUpdate(**update_payload)


_PROFILE_SOURCE_FIELD_ALIASES: dict[str, set[str]] = {
    "presentation_profile": {"presentation_profile", "gender"},
    "fit_preferences": {"fit_preferences", "fit", "fit_preference", "preferred_fit"},
    "silhouette_preferences": {
        "silhouette_preferences",
        "preferred_silhouette",
        "silhouette",
        "silhouettes",
    },
    "comfort_preferences": {"comfort_preferences", "comfort_preference", "comfort", "mobility_preference"},
    "formality_preferences": {
        "formality_preferences",
        "formality_preference",
        "formality",
        "occasion_formality",
        "dress_code",
    },
    "color_preferences": {
        "color_preferences",
        "color_preference",
        "preferred_colors",
        "preferred_palette",
        "palette",
    },
    "color_avoidances": {
        "color_avoidances",
        "avoid_colors",
        "avoided_colors",
        "palette_avoidances",
    },
    "preferred_items": {
        "preferred_items",
        "favorite_items",
        "preferred_garments",
        "wardrobe_items",
    },
    "avoided_items": {
        "avoided_items",
        "avoid_items",
        "avoided_garments",
        "avoid_garments",
        "avoid_hero_garments",
        "excluded_garments",
        "unavailable_garments",
        "forbidden_garments",
    },
}

_KNOWN_PROFILE_SOURCE_KEYS: set[str] = set(_PROFILE_SOURCE_FIELD_ALIASES.keys())
for _aliases in _PROFILE_SOURCE_FIELD_ALIASES.values():
    _KNOWN_PROFILE_SOURCE_KEYS.update(_aliases)


def _touched_profile_fields(
    source: ProfileContext | ProfileContextSnapshot | dict[str, Any] | None,
) -> set[str]:
    if source is None:
        return set()
    if isinstance(source, dict):
        raw_keys = {str(key) for key in source.keys()}
        return {
            field_name
            for field_name, aliases in _PROFILE_SOURCE_FIELD_ALIASES.items()
            if raw_keys.intersection(aliases)
        }
    model_fields_set = getattr(source, "model_fields_set", set())
    if not model_fields_set and isinstance(source, ProfileContextSnapshot):
        raw_keys = set(source.values.keys())
        return {
            field_name
            for field_name, aliases in _PROFILE_SOURCE_FIELD_ALIASES.items()
            if raw_keys.intersection(aliases)
        }
    touched: set[str] = set()
    for field_name in _PROFILE_SOURCE_FIELD_ALIASES:
        if field_name in model_fields_set:
            touched.add(field_name)
    return touched


def _passthrough_profile_payload(
    source: ProfileContext | ProfileContextSnapshot | dict[str, Any] | None,
) -> dict[str, Any]:
    if source is None or isinstance(source, ProfileContext):
        return {}
    payload = source.values if isinstance(source, ProfileContextSnapshot) else source
    return {
        key: value
        for key, value in payload.items()
        if key not in _KNOWN_PROFILE_SOURCE_KEYS and value is not None
    }
