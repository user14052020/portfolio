from typing import Any

from app.application.reasoning.services.profile_context_service import DefaultProfileContextService
from app.application.reasoning.profile_context_models import ProfileContextInput
from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_context import ChatModeContext, OccasionContext
from app.domain.knowledge.entities import KnowledgeQuery


class BuildKnowledgeQueryUseCase:
    def __init__(
        self,
        *,
        profile_context_service: DefaultProfileContextService | None = None,
    ) -> None:
        self._profile_context_service = profile_context_service or DefaultProfileContextService()

    def execute(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        mode: str,
        intent: str | None = None,
        style_id: str | None = None,
        style_name: str | None = None,
        anchor_garment: dict[str, Any] | None = None,
        occasion_context: OccasionContext | dict[str, Any] | None = None,
        diversity_constraints: dict[str, Any] | None = None,
        limit: int = 6,
    ) -> KnowledgeQuery:
        resolved_occasion = occasion_context
        if isinstance(occasion_context, OccasionContext):
            resolved_occasion = occasion_context.model_dump(exclude_none=True)
        profile_snapshot = self._profile_context_service.build_snapshot_sync(
            ProfileContextInput(
                frontend_hints=dict(command.profile_context) or None,
                session_profile=dict(context.session_profile_context) or None,
                persistent_profile=_dict_payload(command.metadata.get("persistent_profile_context")),
                recent_updates=dict(context.profile_recent_updates) or None,
            )
        )
        return KnowledgeQuery(
            mode=mode,
            style_id=style_id or context.current_style_id,
            style_name=style_name or context.current_style_name,
            anchor_garment=anchor_garment,
            occasion_context=resolved_occasion,
            diversity_constraints=dict(diversity_constraints or {}),
            intent=intent,
            limit=limit,
            message=command.normalized_message() or None,
            profile_context=dict(profile_snapshot.values),
        )


def _dict_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {key: item for key, item in value.items() if item is not None}
    return {}
