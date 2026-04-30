from dataclasses import dataclass
from typing import Any

from app.application.reasoning.services.profile_context_service import DefaultProfileContextService
from app.application.reasoning.profile_context_models import ProfileContextInput
from app.domain.chat_context import ChatModeContext
from app.domain.reasoning import ProfileContextSnapshot


@dataclass(frozen=True)
class ProfileSessionState:
    session_profile_context: dict[str, Any]
    profile_context_snapshot: dict[str, Any] | None
    profile_recent_updates: dict[str, Any]
    profile_completeness_state: str


class ProfileSessionStateService:
    def __init__(
        self,
        *,
        profile_context_service: DefaultProfileContextService | None = None,
    ) -> None:
        self._profile_context_service = profile_context_service or DefaultProfileContextService()

    async def resolve(
        self,
        *,
        context: ChatModeContext,
        explicit_profile_context: dict[str, Any] | None,
        metadata: dict[str, Any] | None,
    ) -> ProfileSessionState:
        request_metadata = metadata if isinstance(metadata, dict) else {}
        recent_updates = _dict_payload(request_metadata.get("profile_recent_updates"))
        session_profile = _dict_payload(context.session_profile_context)
        persistent_profile = _dict_payload(request_metadata.get("persistent_profile_context"))
        explicit_profile = _dict_payload(explicit_profile_context)

        request = ProfileContextInput(
            frontend_hints=explicit_profile or None,
            session_profile=session_profile or None,
            persistent_profile=persistent_profile or None,
            recent_updates=recent_updates or None,
        )
        snapshot = await self._profile_context_service.build_snapshot(request)
        normalized_recent_updates = await self._normalized_recent_updates(recent_updates)

        return ProfileSessionState(
            session_profile_context=_compact_profile_payload(snapshot),
            profile_context_snapshot=snapshot.model_dump(mode="json") if snapshot.present else None,
            profile_recent_updates=normalized_recent_updates,
            profile_completeness_state=self._profile_context_service.completeness_state_sync(snapshot),
        )

    async def _normalized_recent_updates(
        self,
        recent_updates: dict[str, Any],
    ) -> dict[str, Any]:
        if not recent_updates:
            return {}
        snapshot = await self._profile_context_service.build_snapshot(
            ProfileContextInput(recent_updates=recent_updates)
        )
        return _compact_profile_payload(snapshot)


def _compact_profile_payload(snapshot: ProfileContextSnapshot) -> dict[str, Any]:
    if not snapshot.present:
        return {}

    payload: dict[str, Any] = {}
    if snapshot.presentation_profile:
        payload["presentation_profile"] = snapshot.presentation_profile

    tuple_fields = {
        "fit_preferences": snapshot.fit_preferences,
        "silhouette_preferences": snapshot.silhouette_preferences,
        "comfort_preferences": snapshot.comfort_preferences,
        "formality_preferences": snapshot.formality_preferences,
        "color_preferences": snapshot.color_preferences,
        "color_avoidances": snapshot.color_avoidances,
        "preferred_items": snapshot.preferred_items,
        "avoided_items": snapshot.avoided_items,
    }
    for field_name, values in tuple_fields.items():
        if values:
            payload[field_name] = list(values)

    for key, value in snapshot.legacy_values.items():
        if key not in payload:
            payload[key] = value

    return payload


def _dict_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {key: item for key, item in value.items() if item is not None}
    return {}
