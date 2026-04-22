from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.domain.chat_retention import ChatRetentionPolicy
from app.models import GenerationJob, UploadedAsset
from app.repositories.chat_messages import chat_messages_repository
from app.repositories.generation_jobs import generation_jobs_repository
from app.repositories.stylist_chat_sessions import stylist_chat_sessions_repository
from app.repositories.stylist_session_states import stylist_session_states_repository
from app.repositories.uploads import uploads_repository


@dataclass(frozen=True, slots=True)
class ChatRetentionCleanupResult:
    cutoff: datetime
    deleted_messages_count: int
    deleted_generation_jobs_count: int
    deleted_uploaded_assets_count: int
    deleted_session_states_count: int
    deleted_chat_sessions_count: int
    deleted_media_files_count: int


class LocalMediaRetentionCleaner:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def delete_uploaded_asset_file(self, asset: UploadedAsset) -> bool:
        if asset.storage_backend != "local":
            return False
        return self._delete_relative_media_path(asset.storage_path)

    def delete_generation_result_file(self, job: GenerationJob) -> bool:
        if not job.result_url:
            return False
        relative_path = self._relative_path_from_public_url(job.result_url)
        if relative_path and self._delete_relative_media_path(relative_path):
            return True
        return self._delete_comfyui_output_file(job.result_url)

    def _relative_path_from_public_url(self, public_url: str) -> str | None:
        media_url = self.settings.media_url.rstrip("/")
        parsed = urlparse(public_url)
        path = parsed.path if parsed.scheme or parsed.netloc else public_url
        if not path.startswith(f"{media_url}/"):
            return None
        return unquote(path[len(media_url) + 1 :])

    def _delete_relative_media_path(self, relative_path: str | None) -> bool:
        return self._delete_relative_path_under_root(self.settings.media_root, relative_path)

    def _delete_comfyui_output_file(self, public_url: str) -> bool:
        if self.settings.comfyui_output_root is None:
            return False

        relative_path = self._relative_comfyui_output_path(public_url)
        if relative_path is None:
            return False
        return self._delete_relative_path_under_root(self.settings.comfyui_output_root, relative_path)

    def _relative_comfyui_output_path(self, public_url: str) -> Path | None:
        parsed = urlparse(public_url)
        comfy_base = urlparse(self.settings.comfyui_base_url)
        if parsed.scheme and parsed.netloc and (parsed.scheme, parsed.netloc) != (comfy_base.scheme, comfy_base.netloc):
            return None
        if parsed.path.rstrip("/") != "/view":
            return None

        query = parse_qs(parsed.query)
        file_type = (query.get("type") or ["output"])[0]
        if file_type != "output":
            return None

        filename = (query.get("filename") or [""])[0].strip()
        if not filename or Path(filename).name != filename:
            return None
        subfolder = (query.get("subfolder") or [""])[0].strip()
        return Path(unquote(subfolder)) / unquote(filename) if subfolder else Path(unquote(filename))

    def _delete_relative_path_under_root(self, root: Path, relative_path: str | Path | None) -> bool:
        if not relative_path:
            return False

        resolved_root = root.resolve()
        candidate = (resolved_root / Path(relative_path)).resolve()
        if candidate != resolved_root and resolved_root not in candidate.parents:
            return False
        if not candidate.is_file():
            return False

        try:
            candidate.unlink()
        except OSError:
            return False
        return True


class ChatRetentionService:
    def __init__(
        self,
        *,
        policy: ChatRetentionPolicy | None = None,
        media_cleaner: LocalMediaRetentionCleaner | None = None,
    ) -> None:
        settings = get_settings()
        self.policy = policy or ChatRetentionPolicy(max_age_days=settings.chat_retention_days)
        self.media_cleaner = media_cleaner or LocalMediaRetentionCleaner(settings)

    def cutoff(self, now: datetime | None = None) -> datetime:
        return self.policy.cutoff(now)

    def is_expired(self, created_at: datetime, now: datetime | None = None) -> bool:
        return self.policy.is_expired(created_at, now)

    async def prune_expired(self, session: AsyncSession, *, now: datetime | None = None) -> ChatRetentionCleanupResult:
        cutoff = self.cutoff(now or datetime.now(timezone.utc))
        expired_jobs = await generation_jobs_repository.list_older_than(session, cutoff)
        expired_job_ids = [job.id for job in expired_jobs]
        expired_assets = await uploads_repository.list_older_than(session, cutoff)
        expired_asset_ids = [asset.id for asset in expired_assets]

        deleted_media_files_count = 0
        for job in expired_jobs:
            if self.media_cleaner.delete_generation_result_file(job):
                deleted_media_files_count += 1

        deleted_messages_count = await chat_messages_repository.delete_older_than(session, cutoff)
        await chat_messages_repository.detach_generation_jobs(session, expired_job_ids)
        deleted_generation_jobs_count = await generation_jobs_repository.delete_by_ids(session, expired_job_ids)

        await chat_messages_repository.detach_uploaded_assets(session, expired_asset_ids)
        await generation_jobs_repository.detach_uploaded_assets(session, expired_asset_ids)

        for asset in expired_assets:
            if self.media_cleaner.delete_uploaded_asset_file(asset):
                deleted_media_files_count += 1

        deleted_uploaded_assets_count = await uploads_repository.delete_by_ids(session, expired_asset_ids)
        deleted_session_states_count = await stylist_session_states_repository.delete_older_than(session, cutoff)
        deleted_chat_sessions_count = await stylist_chat_sessions_repository.delete_inactive_older_than(session, cutoff)
        return ChatRetentionCleanupResult(
            cutoff=cutoff,
            deleted_messages_count=deleted_messages_count,
            deleted_generation_jobs_count=deleted_generation_jobs_count,
            deleted_uploaded_assets_count=deleted_uploaded_assets_count,
            deleted_session_states_count=deleted_session_states_count,
            deleted_chat_sessions_count=deleted_chat_sessions_count,
            deleted_media_files_count=deleted_media_files_count,
        )


chat_retention_service = ChatRetentionService()
