from datetime import UTC, datetime
from uuid import uuid4

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.comfyui import ComfyUIClient
from app.models.enums import GenerationProvider, GenerationStatus
from app.repositories.generation_jobs import generation_jobs_repository
from app.repositories.uploads import uploads_repository
from app.schemas.generation_job import GenerationJobCreate


class GenerationService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.comfyui_client = ComfyUIClient()
        self.redis = redis.from_url(self.settings.redis_url, decode_responses=True)

    async def create_and_submit(self, session: AsyncSession, payload: GenerationJobCreate):
        input_asset = None
        if payload.input_asset_id:
            input_asset = await uploads_repository.get(session, payload.input_asset_id)

        job = await generation_jobs_repository.create(
            session,
            {
                "public_id": f"job_{uuid4().hex[:12]}",
                "session_id": payload.session_id,
                "provider": payload.provider,
                "status": GenerationStatus.PENDING,
                "input_text": payload.input_text,
                "prompt": payload.prompt,
                "recommendation_ru": payload.recommendation_ru,
                "recommendation_en": payload.recommendation_en,
                "input_asset_id": payload.input_asset_id,
                "body_height_cm": payload.body_height_cm,
                "body_weight_kg": payload.body_weight_kg,
                "provider_payload": {},
            },
        )

        if payload.provider == GenerationProvider.MOCK:
            job = await generation_jobs_repository.update(
                session,
                job,
                {
                    "status": GenerationStatus.COMPLETED,
                    "progress": 100,
                    "result_url": "https://placehold.co/1200x1200/f3ede0/111827?text=AI+Stylist+Preview",
                    "started_at": datetime.now(UTC),
                    "completed_at": datetime.now(UTC),
                },
            )
            await self._cache_job(job.public_id, job.status.value, job.progress, job.result_url)
            return job

        try:
            workflow = self.comfyui_client.build_workflow(
                prompt=payload.prompt,
                negative_prompt="blurry, low quality, distorted clothes, cluttered scene",
                input_image_url=input_asset.public_url if input_asset else None,
                body_height_cm=payload.body_height_cm,
                body_weight_kg=payload.body_weight_kg,
            )
            job = await generation_jobs_repository.update(
                session,
                job,
                {
                    "provider_payload": workflow,
                },
            )
            external_job_id = await self.comfyui_client.queue_prompt(workflow)
            job = await generation_jobs_repository.update(
                session,
                job,
                {
                    "status": GenerationStatus.QUEUED,
                    "progress": 10,
                    "external_job_id": external_job_id,
                    "provider_payload": workflow,
                    "started_at": datetime.now(UTC),
                },
            )
        except Exception as exc:
            job = await generation_jobs_repository.update(
                session,
                job,
                {
                    "status": GenerationStatus.FAILED,
                    "progress": 100,
                    "error_message": str(exc),
                    "completed_at": datetime.now(UTC),
                },
            )

        await self._cache_job(job.public_id, job.status.value, job.progress, job.result_url)
        return job

    async def sync_job_status(self, session: AsyncSession, job):
        if job.status in {GenerationStatus.COMPLETED, GenerationStatus.FAILED}:
            return job
        if job.provider == GenerationProvider.MOCK or not job.external_job_id:
            return job

        provider_status = await self.comfyui_client.get_job_status(job.external_job_id)
        updates: dict[str, object] = {
            "status": provider_status.status,
            "progress": provider_status.progress,
        }
        if provider_status.image_url:
            updates["result_url"] = provider_status.image_url
        if provider_status.error_message:
            updates["error_message"] = provider_status.error_message
        if provider_status.status in {GenerationStatus.COMPLETED, GenerationStatus.FAILED}:
            updates["completed_at"] = datetime.now(UTC)

        job = await generation_jobs_repository.update(session, job, updates)
        await self._cache_job(job.public_id, job.status.value, job.progress, job.result_url)
        return job

    async def _cache_job(self, public_id: str, status: str, progress: int, result_url: str | None) -> None:
        try:
            await self.redis.hset(
                f"generation-job:{public_id}",
                mapping={"status": status, "progress": progress, "result_url": result_url or ""},
            )
            await self.redis.expire(f"generation-job:{public_id}", 3600)
        except Exception:
            return


generation_service = GenerationService()
