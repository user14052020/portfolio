from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.product_behavior.services.session_flow_state_service import SessionFlowStateService
from app.application.stylist_chat.contracts.ports import (
    GenerationJobScheduler,
    GenerationScheduleRequest,
    GenerationScheduleResult,
)
from app.domain.chat_context import ChatModeContext
from app.models.enums import GenerationStatus
from app.repositories.generation_jobs import generation_jobs_repository
from app.schemas.generation_job import GenerationJobCreate
from app.services.generation import generation_service


class DefaultGenerationJobScheduler(GenerationJobScheduler):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.session_flow_state_service = SessionFlowStateService()

    async def sync_context(self, context: ChatModeContext) -> ChatModeContext:
        if not context.current_job_id:
            return context
        generation_job = await generation_jobs_repository.get_by_public_id(self.session, context.current_job_id)
        if generation_job is None:
            return context
        return self.session_flow_state_service.sync_generation_status(
            context=context,
            generation_status=generation_job.status,
        )

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
                negative_prompt=request.negative_prompt,
                input_asset_id=request.input_asset_id,
                body_height_cm=self._coerce_int(request.profile_context.get("height_cm")),
                body_weight_kg=self._coerce_int(request.profile_context.get("weight_kg")),
                workflow_name=request.workflow_name,
                workflow_version=request.workflow_version,
                visual_generation_plan=request.visual_generation_plan,
                generation_metadata=request.generation_metadata,
                metadata={
                    **request.metadata,
                    "source_message_id": (
                        request.generation_intent.source_message_id
                        if request.generation_intent is not None
                        else None
                    ),
                },
                idempotency_key=request.idempotency_key,
            ),
        )
        return GenerationScheduleResult(
            job_id=generation_job.public_id,
            status=generation_job.status.value,
            job=generation_job,
        )

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
