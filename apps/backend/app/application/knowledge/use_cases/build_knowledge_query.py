from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_context import ChatModeContext, OccasionContext
from app.domain.knowledge.entities import KnowledgeQuery


class BuildKnowledgeQueryUseCase:
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
            profile_context=dict(command.profile_context),
        )
