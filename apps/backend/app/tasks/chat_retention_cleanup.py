import asyncio
import logging

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.chat_retention import chat_retention_service


logger = logging.getLogger(__name__)


async def run_chat_retention_cleanup(stop_event: asyncio.Event) -> None:
    settings = get_settings()

    while not stop_event.is_set():
        try:
            async with SessionLocal() as session:
                try:
                    result = await chat_retention_service.prune_expired(session)
                    await session.commit()
                    logger.info(
                        "Chat retention cleanup finished",
                        extra={
                            "cutoff": result.cutoff.isoformat(),
                            "deleted_messages_count": result.deleted_messages_count,
                            "deleted_generation_jobs_count": result.deleted_generation_jobs_count,
                            "deleted_uploaded_assets_count": result.deleted_uploaded_assets_count,
                            "deleted_session_states_count": result.deleted_session_states_count,
                            "deleted_chat_sessions_count": result.deleted_chat_sessions_count,
                            "deleted_media_files_count": result.deleted_media_files_count,
                        },
                    )
                except Exception:
                    await session.rollback()
                    raise
        except Exception:
            logger.exception("Chat retention cleanup iteration failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.chat_retention_cleanup_interval_seconds)
        except asyncio.TimeoutError:
            continue
