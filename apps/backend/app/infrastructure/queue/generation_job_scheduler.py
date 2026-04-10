from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.stylist_chat.contracts.ports import (
    GenerationJobScheduler,
    GenerationScheduleRequest,
    GenerationScheduleResult,
)
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import FlowState
from app.models.enums import GenerationStatus
from app.repositories.generation_jobs import generation_jobs_repository
from app.schemas.generation_job import GenerationJobCreate
from app.services.generation import generation_service


class DefaultGenerationJobScheduler(GenerationJobScheduler):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def sync_context(self, context: ChatModeContext) -> ChatModeContext:
        if not context.current_job_id:
            return context
        generation_job = await generation_jobs_repository.get_by_public_id(self.session, context.current_job_id)
        if generation_job is None:
            return context
        context.flow_state = self._flow_state_from_generation_status(generation_job.status)
        return context

    async def enqueue(self, request: GenerationScheduleRequest) -> GenerationScheduleResult:
        existing_job = await generation_jobs_repository.get_latest_active_by_session(self.session, request.session_id)
        if existing_job is not None and existing_job.status in {
            GenerationStatus.PENDING,
            GenerationStatus.QUEUED,
            GenerationStatus.RUNNING,
        }:
            enriched = await generation_service.enrich_job_runtime(self.session, existing_job)
            if self._job_idempotency_key(enriched) == request.idempotency_key:
                return GenerationScheduleResult(
                    job_id=enriched.public_id,
                    status=enriched.status.value,
                    job=enriched,
                )
            return GenerationScheduleResult(
                job_id=enriched.public_id,
                status=enriched.status.value,
                job=enriched,
                blocked_by_active_job=True,
            )

        generation_job = await generation_service.create_and_submit(
            self.session,
            GenerationJobCreate(
                session_id=request.session_id,
                input_text=request.input_text,
                recommendation_ru=request.recommendation_text,
                recommendation_en=request.recommendation_text,
                prompt=request.prompt,
                input_asset_id=request.input_asset_id,
                body_height_cm=self._coerce_int(request.profile_context.get("height_cm")),
                body_weight_kg=self._coerce_int(request.profile_context.get("weight_kg")),
            ),
        )
        provider_payload = generation_job.provider_payload if isinstance(generation_job.provider_payload, dict) else {}
        generation_job = await generation_jobs_repository.update(
            self.session,
            generation_job,
            {
                "provider_payload": {
                    **provider_payload,
                    "_orchestration": {
                        **(
                            provider_payload.get("_orchestration")
                            if isinstance(provider_payload.get("_orchestration"), dict)
                            else {}
                        ),
                        "idempotency_key": request.idempotency_key,
                    },
                }
            },
        )
        return GenerationScheduleResult(
            job_id=generation_job.public_id,
            status=generation_job.status.value,
            job=generation_job,
        )

    def _flow_state_from_generation_status(self, status: GenerationStatus) -> FlowState:
        if status == GenerationStatus.PENDING:
            return FlowState.GENERATION_QUEUED
        if status in {GenerationStatus.QUEUED, GenerationStatus.RUNNING}:
            return FlowState.GENERATION_IN_PROGRESS
        if status == GenerationStatus.COMPLETED:
            return FlowState.COMPLETED
        return FlowState.RECOVERABLE_ERROR

    def _coerce_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    def _job_idempotency_key(self, job: Any) -> str | None:
        provider_payload = job.provider_payload if isinstance(job.provider_payload, dict) else {}
        orchestration = provider_payload.get("_orchestration")
        if not isinstance(orchestration, dict):
            return None
        raw_value = orchestration.get("idempotency_key")
        if isinstance(raw_value, str):
            cleaned = raw_value.strip()
            return cleaned or None
        return None
