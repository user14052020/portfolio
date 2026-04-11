from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.stylist_chat.contracts.ports import StyleHistoryProvider
from app.application.stylist_chat.services.constants import FALLBACK_STYLE_LIBRARY
from app.domain.chat_context import StyleDirectionContext
from app.domain.knowledge.entities import KnowledgeCard
from app.models import StyleDirection
from app.infrastructure.knowledge.repositories.style_catalog_repository import DatabaseStyleCatalogRepository
from app.repositories.style_directions import style_directions_repository
from app.repositories.stylist_style_exposures import stylist_style_exposures_repository


class DatabaseStyleHistoryProvider(StyleHistoryProvider):
    def __init__(self, session: AsyncSession, *, style_catalog_repository: DatabaseStyleCatalogRepository | None = None) -> None:
        self.session = session
        self.style_catalog_repository = style_catalog_repository

    async def get_recent(self, session_id: str) -> list[StyleDirectionContext]:
        recent_styles = await stylist_style_exposures_repository.list_recent_style_directions(
            self.session,
            session_id=session_id,
            limit=5,
        )
        return [self._style_context_from_model(item) for item in recent_styles]

    async def pick_next(
        self,
        *,
        session_id: str,
        style_history: list[StyleDirectionContext],
    ) -> tuple[StyleDirectionContext, Any | None]:
        if self.style_catalog_repository is not None:
            exclude_style_ids = [
                item.style_id
                for item in style_history[-5:]
                if isinstance(item.style_id, str) and item.style_id.strip()
            ]
            catalog_candidates = await self.style_catalog_repository.list_candidate_styles(
                limit=8,
                exclude_style_ids=exclude_style_ids,
            )
            if catalog_candidates:
                return self._style_context_from_card(catalog_candidates[0]), catalog_candidates[0]

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
            style_family=style_direction.title_en.lower(),
            palette=descriptor_parts[:3],
            silhouette_family=descriptor_parts[0] if descriptor_parts else None,
            hero_garments=descriptor_parts[1:3],
            footwear=["loafers"] if "prep" in style_direction.title_en.lower() else ["derby shoes"],
            accessories=["belt"],
            materials=["wool", "cotton"],
            styling_mood=[descriptor_parts[-1]] if descriptor_parts else [],
            composition_type="editorial flat lay",
            background_family="studio",
            layout_density="balanced",
            camera_distance="medium overhead",
            visual_preset="editorial_studio",
        )

    def _style_context_from_card(self, card: KnowledgeCard) -> StyleDirectionContext:
        metadata = card.metadata or {}
        palette = [str(item).strip() for item in metadata.get("palette", []) if str(item).strip()]
        garments = [str(item).strip() for item in metadata.get("hero_garments", []) if str(item).strip()]
        materials = [str(item).strip() for item in metadata.get("materials", []) if str(item).strip()]
        silhouettes = [str(item).strip() for item in metadata.get("silhouettes", []) if str(item).strip()]
        mood = [str(item).strip() for item in metadata.get("mood_keywords", []) if str(item).strip()]
        return StyleDirectionContext(
            style_id=card.style_id,
            style_name=card.title,
            style_family=str(metadata.get("canonical_name") or "").strip() or None,
            palette=palette[:4],
            silhouette_family=(metadata.get("silhouette_family") or (silhouettes[0] if silhouettes else None)),
            hero_garments=garments[:4],
            footwear=[str(item).strip() for item in metadata.get("footwear", []) if str(item).strip()][:3],
            accessories=[str(item).strip() for item in metadata.get("accessories", []) if str(item).strip()][:3],
            materials=materials[:4],
            styling_mood=mood[:3],
            composition_type="editorial flat lay",
            background_family="editorial surface",
            layout_density="balanced",
            camera_distance="medium overhead",
            visual_preset="editorial_studio",
        )
