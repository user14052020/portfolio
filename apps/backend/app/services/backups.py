from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any

import sqlalchemy as sa
from sqlalchemy import DateTime, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import (
    BlogCategory,
    BlogPost,
    ContactRequest,
    KworkReview,
    PageScene,
    Project,
    ProjectMedia,
    SiteSettings,
    StyleIngestionRuntimeSettings,
)


BACKUP_SCHEMA_VERSION = 1
BACKUP_CONTENT_PATH = "data/content.json"
BACKUP_MANIFEST_PATH = "manifest.json"
BACKUP_MEDIA_PREFIX = "media/"

BACKUP_MODELS: tuple[tuple[str, type], ...] = (
    ("site_settings", SiteSettings),
    ("page_scenes", PageScene),
    ("style_ingestion_runtime_settings", StyleIngestionRuntimeSettings),
    ("blog_categories", BlogCategory),
    ("blog_posts", BlogPost),
    ("projects", Project),
    ("project_media", ProjectMedia),
    ("kwork_reviews", KworkReview),
    ("contact_requests", ContactRequest),
)

RESTORE_DELETE_ORDER: tuple[type, ...] = (
    ProjectMedia,
    BlogPost,
    Project,
    BlogCategory,
    KworkReview,
    ContactRequest,
    SiteSettings,
    PageScene,
    StyleIngestionRuntimeSettings,
)


class BackupService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def create_backup_archive(self, session: AsyncSession) -> Path:
        created_at = datetime.now(UTC)
        content = await self._build_content_payload(session, created_at=created_at)

        handle = tempfile.NamedTemporaryFile(prefix="portfolio-backup-", suffix=".zip", delete=False)
        archive_path = Path(handle.name)
        handle.close()

        with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                BACKUP_MANIFEST_PATH,
                json.dumps(
                    {
                        "schema_version": BACKUP_SCHEMA_VERSION,
                        "created_at": created_at.isoformat(),
                        "media_root": self.settings.media_root.as_posix(),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            archive.writestr(
                BACKUP_CONTENT_PATH,
                json.dumps(content, ensure_ascii=False, indent=2),
            )
            for file_path, archive_name in self._iter_media_files():
                archive.write(file_path, archive_name)

        return archive_path

    async def restore_backup_archive(self, session: AsyncSession, archive_path: Path) -> dict[str, Any]:
        with zipfile.ZipFile(archive_path, mode="r") as archive:
            self._validate_archive(archive)
            content = json.loads(archive.read(BACKUP_CONTENT_PATH).decode("utf-8"))
            restored_counts = await self._restore_content(session, content)
            media_files_restored = self._restore_media_files(archive)

        return {
            "restored": restored_counts,
            "media_files_restored": media_files_restored,
            "warnings": [
                "Existing media files not present in the backup were left untouched.",
                "Users, roles, passwords, chat sessions and generation jobs were not restored.",
            ],
        }

    async def _build_content_payload(self, session: AsyncSession, *, created_at: datetime) -> dict[str, Any]:
        tables: dict[str, list[dict[str, Any]]] = {}
        for key, model in BACKUP_MODELS:
            result = await session.execute(select(model).order_by(model.id.asc()))
            tables[key] = [self._serialize_model(instance) for instance in result.scalars().all()]

        return {
            "schema_version": BACKUP_SCHEMA_VERSION,
            "created_at": created_at.isoformat(),
            "tables": tables,
        }

    async def _restore_content(self, session: AsyncSession, content: dict[str, Any]) -> dict[str, int]:
        if int(content.get("schema_version", 0)) != BACKUP_SCHEMA_VERSION:
            raise ValueError("Unsupported backup schema version")

        tables = content.get("tables")
        if not isinstance(tables, dict):
            raise ValueError("Backup content is missing tables")

        for model in RESTORE_DELETE_ORDER:
            await session.execute(sa.delete(model))

        restored_counts: dict[str, int] = {}
        for key, model in BACKUP_MODELS:
            rows = tables.get(key, [])
            if not isinstance(rows, list):
                raise ValueError(f"Backup table {key} must be a list")
            instances = [model(**self._deserialize_row(model, row)) for row in rows]
            session.add_all(instances)
            restored_counts[key] = len(instances)

        await session.flush()
        for _, model in BACKUP_MODELS:
            await self._reset_primary_key_sequence(session, model)

        return restored_counts

    def _iter_media_files(self) -> list[tuple[Path, str]]:
        media_root = self.settings.media_root
        uploads_root = media_root / "uploads"
        if not uploads_root.exists():
            return []

        files: list[tuple[Path, str]] = []
        for file_path in uploads_root.rglob("*"):
            if not file_path.is_file() or file_path.is_symlink():
                continue
            relative_path = file_path.relative_to(media_root).as_posix()
            files.append((file_path, f"{BACKUP_MEDIA_PREFIX}{relative_path}"))
        return files

    def _restore_media_files(self, archive: zipfile.ZipFile) -> int:
        media_root = self.settings.media_root
        media_root.mkdir(parents=True, exist_ok=True)
        media_root_resolved = media_root.resolve()
        restored_count = 0

        for member in archive.infolist():
            if member.is_dir() or not member.filename.startswith(BACKUP_MEDIA_PREFIX):
                continue

            relative_media_path = self._safe_media_relative_path(member.filename)
            if relative_media_path is None:
                raise ValueError(f"Unsafe media path in backup: {member.filename}")

            target_path = (media_root / relative_media_path).resolve()
            if target_path != media_root_resolved and media_root_resolved not in target_path.parents:
                raise ValueError(f"Media path escapes media root: {member.filename}")

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member, mode="r") as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)
            restored_count += 1

        return restored_count

    def _validate_archive(self, archive: zipfile.ZipFile) -> None:
        names = set(archive.namelist())
        if BACKUP_MANIFEST_PATH not in names or BACKUP_CONTENT_PATH not in names:
            raise ValueError("Backup archive is missing manifest or content data")

        manifest = json.loads(archive.read(BACKUP_MANIFEST_PATH).decode("utf-8"))
        if int(manifest.get("schema_version", 0)) != BACKUP_SCHEMA_VERSION:
            raise ValueError("Unsupported backup schema version")

        for member_name in names:
            if member_name.startswith(BACKUP_MEDIA_PREFIX) and self._safe_media_relative_path(member_name) is None:
                raise ValueError(f"Unsafe media path in backup: {member_name}")

    def _safe_media_relative_path(self, archive_name: str) -> Path | None:
        try:
            pure_path = PurePosixPath(archive_name)
            relative_path = pure_path.relative_to(BACKUP_MEDIA_PREFIX.rstrip("/"))
        except ValueError:
            return None

        if not relative_path.parts or any(part in {"", ".", ".."} for part in relative_path.parts):
            return None
        return Path(*relative_path.parts)

    def _serialize_model(self, instance: Any) -> dict[str, Any]:
        return {
            column.name: self._serialize_value(getattr(instance, column.name))
            for column in instance.__table__.columns
        }

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        return value

    def _deserialize_row(self, model: type, row: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(row, dict):
            raise ValueError(f"Backup row for {model.__tablename__} must be an object")

        columns = {column.name: column for column in model.__table__.columns}
        restored: dict[str, Any] = {}
        for key, value in row.items():
            column = columns.get(key)
            if column is None:
                continue
            if value is not None and isinstance(column.type, DateTime):
                restored[key] = datetime.fromisoformat(str(value))
            else:
                restored[key] = value
        return restored

    async def _reset_primary_key_sequence(self, session: AsyncSession, model: type) -> None:
        table_name = model.__tablename__
        primary_key_columns = list(model.__table__.primary_key.columns)
        if len(primary_key_columns) != 1:
            return

        primary_key_name = primary_key_columns[0].name
        await session.execute(
            sa.text(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table_name}', '{primary_key_name}'),
                    COALESCE((SELECT MAX({primary_key_name}) FROM {table_name}), 1),
                    (SELECT COUNT(*) FROM {table_name}) > 0
                )
                """
            )
        )


backup_service = BackupService()
