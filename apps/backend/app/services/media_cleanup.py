from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models import (
    BlogPost,
    ChatMessage,
    ContactRequest,
    GenerationJob,
    KworkReview,
    PageScene,
    Project,
    ProjectMedia,
    SiteSettings,
    UploadedAsset,
)


@dataclass(frozen=True, slots=True)
class MediaCleanupResult:
    scanned_files_count: int
    referenced_files_count: int
    orphan_files_count: int
    deleted_files_count: int = 0
    deleted_uploaded_asset_rows_count: int = 0
    deleted_paths: list[str] = field(default_factory=list)
    skipped_paths: list[str] = field(default_factory=list)


class MediaCleanupService:
    content_reference_models = (
        SiteSettings,
        PageScene,
        Project,
        ProjectMedia,
        BlogPost,
        KworkReview,
        ContactRequest,
    )

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def prune_unreferenced_uploads(
        self,
        session: AsyncSession,
        *,
        dry_run: bool = False,
    ) -> MediaCleanupResult:
        existing_paths = self._list_upload_paths()
        referenced_paths = await self.collect_referenced_media_paths(session)
        orphan_paths = sorted(existing_paths - referenced_paths)

        if dry_run:
            return MediaCleanupResult(
                scanned_files_count=len(existing_paths),
                referenced_files_count=len(existing_paths & referenced_paths),
                orphan_files_count=len(orphan_paths),
                deleted_paths=orphan_paths,
            )

        deleted_paths: list[str] = []
        skipped_paths: list[str] = []
        for relative_path in orphan_paths:
            if self._delete_upload_path(relative_path):
                deleted_paths.append(relative_path)
            else:
                skipped_paths.append(relative_path)

        deleted_asset_rows = await self._delete_uploaded_asset_rows(session, deleted_paths)
        return MediaCleanupResult(
            scanned_files_count=len(existing_paths),
            referenced_files_count=len(existing_paths & referenced_paths),
            orphan_files_count=len(orphan_paths),
            deleted_files_count=len(deleted_paths),
            deleted_uploaded_asset_rows_count=deleted_asset_rows,
            deleted_paths=deleted_paths,
            skipped_paths=skipped_paths,
        )

    async def collect_referenced_media_paths(self, session: AsyncSession) -> set[str]:
        referenced_paths: set[str] = set()

        for model in self.content_reference_models:
            result = await session.execute(select(model))
            for instance in result.scalars().all():
                for column in instance.__table__.columns:
                    referenced_paths.update(self.extract_media_paths(getattr(instance, column.name)))

        referenced_paths.update(await self._collect_operational_media_paths(session))
        return referenced_paths

    def extract_media_paths(self, value: Any) -> set[str]:
        paths: set[str] = set()
        self._extract_media_paths(value, paths)
        return paths

    async def _collect_operational_media_paths(self, session: AsyncSession) -> set[str]:
        paths: set[str] = set()

        chat_asset_ids = select(ChatMessage.uploaded_asset_id).where(ChatMessage.uploaded_asset_id.is_not(None))
        generation_asset_ids = select(GenerationJob.input_asset_id).where(GenerationJob.input_asset_id.is_not(None))

        for statement in (
            select(UploadedAsset.storage_path).where(UploadedAsset.id.in_(chat_asset_ids)),
            select(UploadedAsset.storage_path).where(UploadedAsset.id.in_(generation_asset_ids)),
            select(GenerationJob.result_url).where(GenerationJob.result_url.is_not(None)),
        ):
            result = await session.execute(statement)
            for value in result.scalars().all():
                paths.update(self.extract_media_paths(value))

        return paths

    def _extract_media_paths(self, value: Any, paths: set[str]) -> None:
        if value is None:
            return

        if isinstance(value, dict):
            for item in value.values():
                self._extract_media_paths(item, paths)
            return

        if isinstance(value, (list, tuple, set)):
            for item in value:
                self._extract_media_paths(item, paths)
            return

        if not isinstance(value, str):
            return

        direct_path = self._normalize_media_reference(value)
        if direct_path is not None:
            paths.add(direct_path)

        for match in self._media_reference_pattern().finditer(value):
            matched_path = self._normalize_media_reference(match.group(0))
            if matched_path is not None:
                paths.add(matched_path)

    def _normalize_media_reference(self, value: str) -> str | None:
        stripped = value.strip().strip("\"'")
        if not stripped:
            return None

        media_url = self.settings.media_url.rstrip("/")
        parsed = urlparse(stripped)
        path = parsed.path if parsed.scheme or parsed.netloc else stripped.split("?", 1)[0].split("#", 1)[0]
        path = unquote(path)

        if path.startswith(f"{media_url}/"):
            return self._normalize_relative_path(path[len(media_url) + 1 :])

        return self._normalize_relative_path(path)

    def _normalize_relative_path(self, value: str) -> str | None:
        normalized = value.replace("\\", "/").lstrip("/")
        if not normalized.startswith("uploads/"):
            return None

        relative_path = Path(normalized)
        if any(part in {"", ".", ".."} for part in relative_path.parts):
            return None

        return relative_path.as_posix()

    def _media_reference_pattern(self) -> re.Pattern[str]:
        media_url = re.escape(self.settings.media_url.rstrip("/"))
        return re.compile(rf"(?:https?://[^\s\"'<>]+)?{media_url}/[^\s\"'<>),]+")

    def _list_upload_paths(self) -> set[str]:
        uploads_root = self.settings.media_root / "uploads"
        if not uploads_root.exists():
            return set()

        media_root = self.settings.media_root.resolve()
        paths: set[str] = set()
        for file_path in uploads_root.rglob("*"):
            if not file_path.is_file() or file_path.is_symlink():
                continue
            resolved_path = file_path.resolve()
            if resolved_path != media_root and media_root not in resolved_path.parents:
                continue
            paths.add(resolved_path.relative_to(media_root).as_posix())
        return paths

    def _delete_upload_path(self, relative_path: str) -> bool:
        normalized_path = self._normalize_relative_path(relative_path)
        if normalized_path is None:
            return False

        media_root = self.settings.media_root.resolve()
        file_path = (media_root / normalized_path).resolve()
        if file_path == media_root or media_root not in file_path.parents:
            return False
        if not file_path.is_file():
            return False

        try:
            file_path.unlink()
        except OSError:
            return False
        return True

    async def _delete_uploaded_asset_rows(self, session: AsyncSession, storage_paths: list[str]) -> int:
        if not storage_paths:
            return 0

        result = await session.execute(delete(UploadedAsset).where(UploadedAsset.storage_path.in_(storage_paths)))
        await session.flush()
        return int(result.rowcount or 0)


media_cleanup_service = MediaCleanupService()
