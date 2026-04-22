from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, StylistChatSession
from app.repositories.base import BaseRepository
from app.services.client_request_meta import ClientRequestMeta


class StylistChatSessionsRepository(BaseRepository[StylistChatSession]):
    def __init__(self) -> None:
        super().__init__(StylistChatSession)

    async def get_by_session_id(
        self,
        session: AsyncSession,
        session_id: str,
    ) -> StylistChatSession | None:
        result = await session.execute(
            select(StylistChatSession).where(StylistChatSession.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        session: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 50,
        query: str | None = None,
        active_from: datetime | None = None,
    ) -> list[StylistChatSession]:
        statement = self._apply_filters(select(StylistChatSession), query=query)
        statement = self._apply_active_from(statement, active_from=active_from)
        statement = (
            statement.order_by(
                StylistChatSession.last_message_at.desc().nullslast(),
                StylistChatSession.updated_at.desc(),
                StylistChatSession.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def count_sessions(
        self,
        session: AsyncSession,
        *,
        query: str | None = None,
        active_from: datetime | None = None,
    ) -> int:
        statement = self._apply_filters(select(func.count(StylistChatSession.id)), query=query)
        statement = self._apply_active_from(statement, active_from=active_from)
        return int((await session.scalar(statement)) or 0)

    async def delete_inactive_older_than(self, session: AsyncSession, cutoff: datetime) -> int:
        result = await session.execute(
            delete(StylistChatSession).where(
                or_(
                    StylistChatSession.last_message_at.is_(None),
                    StylistChatSession.last_message_at < cutoff,
                ),
                StylistChatSession.updated_at < cutoff,
            )
        )
        await session.flush()
        return int(result.rowcount or 0)

    async def upsert_activity(
        self,
        session: AsyncSession,
        *,
        session_id: str,
        locale: str | None,
        request_meta: ClientRequestMeta | None,
        active_mode: str | None,
        decision_type: str | None,
        message_increment: int,
        metadata: dict[str, Any] | None = None,
    ) -> StylistChatSession:
        existing = await self.get_by_session_id(session, session_id)
        stats = await self._message_stats(session, session_id)
        started_at = stats["first_message_at"] or datetime.now(timezone.utc)
        last_message_at = stats["last_message_at"] or datetime.now(timezone.utc)
        current_count = int(stats["message_count"] or 0)
        meta = request_meta or ClientRequestMeta()

        if existing is None:
            existing = StylistChatSession(
                session_id=session_id,
                started_at=started_at,
                last_message_at=last_message_at,
                message_count=current_count,
                locale=locale,
                client_ip=meta.client_ip,
                client_user_agent=meta.client_user_agent,
                last_active_mode=active_mode,
                last_decision_type=decision_type,
                metadata_json=self._build_metadata(existing=None, request_meta=meta, metadata=metadata),
            )
            session.add(existing)
            await session.flush()
            return existing

        previous_count = existing.message_count or 0
        existing.last_message_at = last_message_at
        existing.message_count = (
            current_count
            if current_count > previous_count
            else previous_count + max(message_increment, 0)
        )
        existing.locale = locale or existing.locale
        existing.client_ip = meta.client_ip or existing.client_ip
        existing.client_user_agent = meta.client_user_agent or existing.client_user_agent
        existing.last_active_mode = active_mode or existing.last_active_mode
        existing.last_decision_type = decision_type or existing.last_decision_type
        existing.metadata_json = self._build_metadata(existing=existing, request_meta=meta, metadata=metadata)
        await session.flush()
        return existing

    async def _message_stats(self, session: AsyncSession, session_id: str) -> dict[str, Any]:
        result = await session.execute(
            select(
                func.count(ChatMessage.id),
                func.min(ChatMessage.created_at),
                func.max(ChatMessage.created_at),
            ).where(ChatMessage.session_id == session_id)
        )
        message_count, first_message_at, last_message_at = result.one()
        return {
            "message_count": int(message_count or 0),
            "first_message_at": first_message_at,
            "last_message_at": last_message_at,
        }

    def _build_metadata(
        self,
        *,
        existing: StylistChatSession | None,
        request_meta: ClientRequestMeta,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        base = dict(existing.metadata_json) if existing is not None and isinstance(existing.metadata_json, dict) else {}
        base.update(metadata or {})
        if request_meta.request_origin:
            base["last_request_origin"] = request_meta.request_origin
        base["last_seen_at"] = datetime.now(timezone.utc).isoformat()
        return base

    def _apply_filters(self, statement, *, query: str | None):
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return statement
        pattern = f"%{cleaned_query}%"
        return statement.where(
            or_(
                StylistChatSession.session_id.ilike(pattern),
                StylistChatSession.client_ip.ilike(pattern),
                StylistChatSession.locale.ilike(pattern),
                StylistChatSession.last_active_mode.ilike(pattern),
                StylistChatSession.last_decision_type.ilike(pattern),
            )
        )

    def _apply_active_from(self, statement, *, active_from: datetime | None):
        if active_from is None:
            return statement
        return statement.where(
            or_(
                StylistChatSession.last_message_at >= active_from,
                StylistChatSession.updated_at >= active_from,
            )
        )


stylist_chat_sessions_repository = StylistChatSessionsRepository()
