from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.stylist_chat.contracts.ports import StyleHistoryProvider
from app.application.stylist_chat.services.constants import FALLBACK_STYLE_LIBRARY
from app.domain.chat_context import StyleDirectionContext
from app.models import StyleDirection
from app.repositories.style_directions import style_directions_repository
from app.repositories.stylist_style_exposures import stylist_style_exposures_repository


class DatabaseStyleHistoryProvider(StyleHistoryProvider):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_recent(self, session_id: str) -> list[StyleDirectionContext]:
        today = datetime.now(timezone.utc).date()
        styles = await style_directions_repository.list_active_not_shown_today(
            self.session,
            session_id=session_id,
            shown_on=today,
        )
        return [self._style_context_from_model(item) for item in styles[:5]]

    async def pick_next(
        self,
        *,
        session_id: str,
        style_history: list[StyleDirectionContext],
    ) -> tuple[StyleDirectionContext, Any | None]:
        recent_style_keys = {
            item.style_id or item.style_name for item in style_history[-5:] if item.style_id or item.style_name
        }
        today = datetime.now(timezone.utc).date()
        candidates = await style_directions_repository.list_active_not_shown_today(
            self.session,
            session_id=session_id,
            shown_on=today,
        )
        if not candidates:
            candidates = await style_directions_repository.list_active(self.session)
        for candidate in candidates:
            if candidate.slug not in recent_style_keys and candidate.title_en not in recent_style_keys:
                return self._style_context_from_model(candidate), candidate
        if candidates:
            return self._style_context_from_model(candidates[0]), candidates[0]
        fallback = FALLBACK_STYLE_LIBRARY[len(style_history) % len(FALLBACK_STYLE_LIBRARY)]
        return StyleDirectionContext.model_validate(fallback), None

    async def record_exposure(self, *, session_id: str, style_direction: Any) -> None:
        if not isinstance(style_direction, StyleDirection):
            return
        today = datetime.now(timezone.utc).date()
        existing = await stylist_style_exposures_repository.get_for_session_day_and_style(
            self.session,
            session_id=session_id,
            style_direction_id=style_direction.id,
            shown_on=today,
        )
        if existing is None:
            await stylist_style_exposures_repository.create(
                self.session,
                {
                    "session_id": session_id,
                    "style_direction_id": style_direction.id,
                    "shown_on": today,
                },
            )

    def _style_context_from_model(self, style_direction: StyleDirection) -> StyleDirectionContext:
        descriptor_parts = [item.strip() for item in style_direction.descriptor_en.split(",") if item.strip()]
        return StyleDirectionContext(
            style_id=style_direction.slug,
            style_name=style_direction.title_en,
            palette=descriptor_parts[:3],
            silhouette=descriptor_parts[0] if descriptor_parts else None,
            hero_garments=descriptor_parts[1:3],
            styling_mood=descriptor_parts[-1] if descriptor_parts else None,
            composition_type="editorial flat lay",
            background_family="studio",
        )
