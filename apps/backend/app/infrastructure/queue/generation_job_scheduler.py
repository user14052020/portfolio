from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.product_behavior.services.session_flow_state_service import SessionFlowStateService
from app.application.stylist_chat.contracts.ports import (
    GenerationJobScheduler,
    GenerationScheduleRequest,
    GenerationScheduleResult,
)
from app.domain.chat_context import ChatModeContext
from app.domain.usage_access_policy import (
    USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT,
    RequestedAction,
)
from app.infrastructure.observability.runtime_policy_observability import RuntimePolicyObservability
from app.models.enums import GenerationStatus
from app.repositories.generation_jobs import generation_jobs_repository
from app.schemas.generation_job import GenerationJobCreate
from app.services.chat_retention import chat_retention_service
from app.services.generation import generation_service
from app.services.usage_access_policy import UsageAccessPolicyService


class DefaultGenerationJobScheduler(GenerationJobScheduler):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.session_flow_state_service = SessionFlowStateService()
        self.usage_access_policy_service = UsageAccessPolicyService()
        self.runtime_policy_observability = RuntimePolicyObservability()

    async def sync_context(self, context: ChatModeContext) -> ChatModeContext:
        if not context.current_job_id:
            return context
        generation_job = await generation_jobs_repository.get_by_public_id(
            self.session,
            context.current_job_id,
            created_at_from=chat_retention_service.cutoff(),
        )
        if generation_job is None:
            return context
        return self.session_flow_state_service.sync_generation_status(
            context=context,
            generation_status=generation_job.status,
        )

    async def enqueue(self, request: GenerationScheduleRequest) -> GenerationScheduleResult:
        existing_job = await generation_jobs_repository.get_latest_active_by_session(
            self.session,
            request.session_id,
            created_at_from=chat_retention_service.cutoff(),
        )
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

        subject = self.usage_access_policy_service.build_subject(
            session_id=request.session_id,
            metadata=request.metadata,
            trusted_metadata=True,
        )
        access_decision = await self.usage_access_policy_service.evaluate(
            self.session,
            subject=subject,
            action=RequestedAction(action_type="generation"),
        )
        await self.runtime_policy_observability.record_usage_access_decision(
            subject=subject,
            action_type="generation",
            decision=access_decision,
            surface="generation_scheduler",
        )
        if not access_decision.is_allowed:
            return GenerationScheduleResult(
                job_id=None,
                status="denied",
                job=None,
                notice_text=self._usage_limit_notice(
                    locale=request.locale,
                    denial_reason=access_decision.denial_reason,
                ),
                notice_replaces_text=access_decision.denial_reason == USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT,
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
                client_ip=self._optional_text(request.request_metadata.get("client_ip")),
                client_user_agent=self._optional_text(request.request_metadata.get("client_user_agent")),
                request_origin=self._optional_text(request.request_metadata.get("request_origin")),
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

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip()
        return cleaned or None

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

    def _usage_limit_notice(self, *, locale: str, denial_reason: str | None) -> str:
        if denial_reason == USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT:
            return (
                "На сегодня лимит генераций исчерпан. Текстовые рекомендации останутся доступны, а визуализацию можно будет запустить позже."
                if locale == "ru"
                else "Today's generation limit has been reached. Text recommendations stay available, and visualization can be started later."
            )
        return (
            "Сейчас генерацию запустить нельзя. Попробуйте позже."
            if locale == "ru"
            else "Generation cannot be started right now. Please try again later."
        )
