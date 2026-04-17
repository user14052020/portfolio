import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.visual_generation.services.comfy_generation_orchestrator import ComfyGenerationOrchestrator
from app.application.visual_generation.services.generation_metadata_recorder import GenerationMetadataRecorder
from app.application.visual_generation.use_cases.persist_generation_result import PersistGenerationResultUseCase
from app.application.visual_generation.use_cases.run_generation_job import RunGenerationJobUseCase
from app.core.config import get_settings
from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan
from app.infrastructure.comfy.adapters.comfy_generation_adapter import ComfyGenerationAdapter
from app.infrastructure.comfy.client.comfy_client import ComfyClient
from app.infrastructure.persistence.generation_metadata_store import GenerationJobMetadataStore
from app.models.enums import GenerationProvider, GenerationStatus
from app.repositories.generation_jobs import generation_jobs_repository
from app.repositories.uploads import uploads_repository
from app.schemas.generation_job import GenerationJobCreate, StyleExplanationRead


logger = logging.getLogger(__name__)
UTC = timezone.utc


class QueueRefreshCooldownError(RuntimeError):
    def __init__(self, *, retry_after_seconds: int, next_available_at: datetime) -> None:
        super().__init__("Queue position refresh is on cooldown")
        self.retry_after_seconds = retry_after_seconds
        self.next_available_at = next_available_at


class GenerationService:
    QUEUE_DISPATCH_LOCK_KEY = "generation-queue:dispatch-lock"
    QUEUE_REFRESH_KEY_PREFIX = "generation-queue:refresh:"

    def __init__(
        self,
        *,
        settings=None,
        comfy_client: ComfyClient | None = None,
        generation_backend_adapter: ComfyGenerationAdapter | None = None,
        redis_client=None,
    ) -> None:
        self.settings = settings or get_settings()
        self.comfyui_client = comfy_client or ComfyClient()
        self.generation_backend_adapter = generation_backend_adapter or ComfyGenerationAdapter(client=self.comfyui_client)
        self.run_generation_job = RunGenerationJobUseCase(
            generation_backend_adapter=self.generation_backend_adapter
        )
        self.redis = redis_client or redis.from_url(self.settings.redis_url, decode_responses=True)

    async def create_and_submit(self, session: AsyncSession, payload: GenerationJobCreate):
        existing_active_job = None
        if payload.session_id:
            existing_active_job = await generation_jobs_repository.get_latest_active_by_session(session, payload.session_id)
            if existing_active_job:
                existing_active_job = await self.sync_job_status(session, existing_active_job)
                if self._is_active(existing_active_job.status):
                    existing_active_job = await self._update_job(
                        session,
                        existing_active_job,
                        {},
                        action="duplicate_generation_blocked",
                        details={
                            "session_id": payload.session_id,
                            "reason": "active_generation_job_already_exists_for_session",
                        },
                    )
                    return await self.enrich_job_runtime(session, existing_active_job)

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
                "provider_payload": self._build_initial_provider_payload(payload),
                "operation_log": [
                    self._log_entry(
                        "job_created",
                        details={
                            "provider": payload.provider.value,
                            "session_id": payload.session_id,
                        },
                    )
                ],
            },
        )

        job = await self._update_job(
            session,
            job,
            {
                "progress": 0,
            },
            action="job_enqueued_locally",
            details={"provider": payload.provider.value},
        )
        await self.promote_pending_jobs(session)
        refreshed_job = await generation_jobs_repository.get_by_public_id(session, job.public_id)
        if refreshed_job is None:
            refreshed_job = job
        await self._cache_job(refreshed_job.public_id, refreshed_job.status.value, refreshed_job.progress, refreshed_job.result_url)
        return await self.enrich_job_runtime(session, refreshed_job)

    async def sync_job_status(self, session: AsyncSession, job):
        if self._is_terminal(job.status):
            return job
        timed_out_job = await self._stop_job_if_timed_out(session, job)
        if timed_out_job is not None:
            await self._cache_job(
                timed_out_job.public_id,
                timed_out_job.status.value,
                timed_out_job.progress,
                timed_out_job.result_url,
            )
            return timed_out_job
        if job.provider == GenerationProvider.MOCK or not job.external_job_id:
            return job

        provider_status = await self.comfyui_client.get_job_status(job.external_job_id)
        provider_payload = self._decorate_provider_payload(job, provider_status)
        provider_payload = self._merge_generation_metadata(
            job=job,
            provider_payload=provider_payload,
            status=provider_status.status,
            result_url=provider_status.image_url,
        )
        stale_failure = await self._fail_stalled_comfyui_job_if_needed(
            session=session,
            job=job,
            provider_status=provider_status,
            provider_payload=provider_payload,
        )
        if stale_failure is not None:
            await self._cache_job(
                stale_failure.public_id,
                stale_failure.status.value,
                stale_failure.progress,
                stale_failure.result_url,
            )
            return stale_failure
        status_changed = provider_status.status != job.status
        updates: dict[str, object] = {
            "status": provider_status.status,
            "progress": provider_status.progress,
        }
        if provider_status.image_url:
            updates["result_url"] = provider_status.image_url
        if provider_status.error_message:
            updates["error_message"] = provider_status.error_message
        updates["provider_payload"] = provider_payload
        if provider_status.status in {GenerationStatus.COMPLETED, GenerationStatus.FAILED, GenerationStatus.CANCELLED}:
            updates["completed_at"] = datetime.now(UTC)

        job = await self._update_job(
            session,
            job,
            updates,
            action="provider_status_synced" if status_changed else None,
            details={
                "status": provider_status.status.value,
                "progress": provider_status.progress,
            }
            if status_changed
            else None,
        )
        await self._cache_job(job.public_id, job.status.value, job.progress, job.result_url)
        return job

    async def cancel_job(self, session: AsyncSession, job, *, actor: str = "admin"):
        job = await self.sync_job_status(session, job)
        if self._is_terminal(job.status):
            job = await self._update_job(
                session,
                job,
                {},
                action="cancel_skipped",
                actor=actor,
                details={"reason": "job_already_terminal", "status": job.status.value},
            )
            return await self.enrich_job_runtime(session, job)

        await self._cancel_provider_job(job)
        job = await self._update_job(
            session,
            job,
            {
                "status": GenerationStatus.CANCELLED,
                "progress": 100,
                "error_message": "Generation was cancelled by an administrator.",
                "completed_at": datetime.now(UTC),
            },
            action="job_cancelled",
            actor=actor,
        )
        await self._cache_job(job.public_id, job.status.value, job.progress, job.result_url)
        await self.promote_pending_jobs(session)
        return await self.enrich_job_runtime(session, job)

    async def delete_job(self, session: AsyncSession, job, *, actor: str = "admin"):
        if self._is_active(job.status):
            job = await self.cancel_job(session, job, actor=actor)

        job = await self._update_job(
            session,
            job,
            {
                "deleted_at": datetime.now(UTC),
            },
            action="job_deleted",
            actor=actor,
        )
        return await self.enrich_job_runtime(session, job)

    async def sync_active_jobs(self, session: AsyncSession) -> None:
        active_jobs = await generation_jobs_repository.list_active_jobs(session)
        for job in active_jobs:
            try:
                await self.sync_job_status(session, job)
            except Exception:
                logger.exception("Failed to sync generation job %s", job.public_id)
        await self.promote_pending_jobs(session)

    async def promote_pending_jobs(self, session: AsyncSession):
        lock = self.redis.lock(
            self.QUEUE_DISPATCH_LOCK_KEY,
            timeout=max(self.settings.generation_dispatch_lock_timeout_seconds, 5),
            blocking_timeout=1,
        )
        acquired = False
        try:
            try:
                acquired = bool(await lock.acquire())
            except Exception:
                logger.exception("Failed to acquire generation queue dispatch lock; skipping queue promotion for this cycle")
                return None

            if not acquired:
                return None

            active_provider_job = await generation_jobs_repository.get_oldest_provider_active_job(session)
            if active_provider_job is not None:
                return await self.enrich_job_runtime(session, active_provider_job)

            next_pending_job = await generation_jobs_repository.get_oldest_pending_job(session)
            if next_pending_job is None:
                return None

            submitted_job = await self._submit_pending_job(session, next_pending_job)
            await self._cache_job(submitted_job.public_id, submitted_job.status.value, submitted_job.progress, submitted_job.result_url)
            return await self.enrich_job_runtime(session, submitted_job)
        finally:
            if acquired:
                try:
                    await lock.release()
                except Exception:
                    logger.exception("Failed to release generation queue dispatch lock")

    async def enrich_job_runtime(self, session: AsyncSession, job):
        queue_position = None
        queue_ahead = None
        queue_total = None

        if job.deleted_at is None and job.status == GenerationStatus.PENDING:
            queue_ahead = await generation_jobs_repository.count_pending_jobs_ahead(session, job)
            queue_total = await generation_jobs_repository.count_pending_jobs(session)
            queue_position = queue_ahead + 1

        queue_refresh_available_at, queue_refresh_retry_after_seconds = await self._get_queue_refresh_window(job.public_id)
        setattr(job, "queue_position", queue_position)
        setattr(job, "queue_ahead", queue_ahead)
        setattr(job, "queue_total", queue_total)
        setattr(job, "queue_refresh_available_at", queue_refresh_available_at)
        setattr(job, "queue_refresh_retry_after_seconds", queue_refresh_retry_after_seconds)
        provider_payload = job.provider_payload if isinstance(job.provider_payload, dict) else {}
        setattr(job, "visual_generation_plan", provider_payload.get("_visual_generation_plan"))
        setattr(job, "generation_metadata", provider_payload.get("_generation_metadata"))
        setattr(job, "style_explanation", self._build_style_explanation(job))
        return job

    async def refresh_pending_job_queue_position(self, session: AsyncSession, job):
        await self._enforce_queue_refresh_cooldown(job.public_id)
        await self.sync_active_jobs(session)
        refreshed_job = await generation_jobs_repository.get_by_public_id(session, job.public_id)
        if refreshed_job is None:
            refreshed_job = job
        return await self.enrich_job_runtime(session, refreshed_job)

    async def _cache_job(self, public_id: str, status: str, progress: int, result_url: str | None) -> None:
        try:
            await self.redis.hset(
                f"generation-job:{public_id}",
                mapping={"status": status, "progress": progress, "result_url": result_url or ""},
            )
            await self.redis.expire(f"generation-job:{public_id}", 3600)
        except Exception:
            return

    def _is_terminal(self, status: GenerationStatus) -> bool:
        return status in {GenerationStatus.COMPLETED, GenerationStatus.FAILED, GenerationStatus.CANCELLED}

    def _is_active(self, status: GenerationStatus) -> bool:
        return status in {GenerationStatus.PENDING, GenerationStatus.QUEUED, GenerationStatus.RUNNING}

    async def _submit_pending_job(self, session: AsyncSession, job):
        if job.provider == GenerationProvider.MOCK:
            return await self._update_job(
                session,
                job,
                {
                    "status": GenerationStatus.COMPLETED,
                    "progress": 100,
                    "result_url": "https://placehold.co/1200x1200/f3ede0/111827?text=AI+Stylist+Preview",
                    "started_at": datetime.now(UTC),
                    "completed_at": datetime.now(UTC),
                },
                action="mock_job_completed",
            )

        input_asset = None
        if job.input_asset_id:
            input_asset = await uploads_repository.get(session, job.input_asset_id)

        try:
            existing_provider_payload = job.provider_payload if isinstance(job.provider_payload, dict) else {}
            visual_plan = self._extract_visual_generation_plan(job)
            recorder = GenerationMetadataRecorder(store=GenerationJobMetadataStore(session))
            generation_orchestrator = ComfyGenerationOrchestrator(
                run_generation_job=self.run_generation_job,
                persist_generation_result=PersistGenerationResultUseCase(
                    generation_metadata_recorder=recorder
                ),
            )
            generation_metadata = self._extract_generation_metadata(job=job, plan=visual_plan)
            orchestration = await generation_orchestrator.prepare_generation(
                job=job,
                plan=visual_plan,
                metadata=generation_metadata,
                input_image_url=input_asset.public_url if input_asset else None,
                body_height_cm=job.body_height_cm,
                body_weight_kg=job.body_weight_kg,
            )
            job = orchestration.job
            visual_plan = orchestration.plan
            generation_metadata = orchestration.metadata
            prepared_run = orchestration.prepared_run
            self._log_generation_trace(
                "generation_run_prepared",
                job=job,
                metadata=generation_metadata,
            )
            workflow_with_metadata = {
                **prepared_run.workflow_payload,
                **{key: value for key, value in existing_provider_payload.items() if str(key).startswith("_")},
                "_visual_generation_plan": visual_plan.model_dump(mode="json"),
                "_generation_metadata": generation_metadata.model_dump(mode="json"),
            }
            job = await self._update_job(
                session,
                job,
                {
                    "provider_payload": workflow_with_metadata,
                },
                action="workflow_built",
                details={"template": prepared_run.workflow_version},
            )
            external_job_id = await self.generation_backend_adapter.submit(
                workflow_payload=prepared_run.workflow_payload
            )
            job = await self._update_job(
                session,
                job,
                {
                    "status": GenerationStatus.QUEUED,
                    "progress": 20,
                    "external_job_id": external_job_id,
                    "provider_payload": workflow_with_metadata,
                    "started_at": datetime.now(UTC),
                    "error_message": None,
                },
                action="provider_job_submitted",
                details={"external_job_id": external_job_id},
            )
            self._log_generation_trace(
                "generation_run_submitted",
                job=job,
                metadata=generation_metadata,
                extra={"external_job_id": external_job_id},
            )
            return job
        except Exception as exc:
            return await self._update_job(
                session,
                job,
                {
                    "status": GenerationStatus.FAILED,
                    "progress": 100,
                    "error_message": str(exc),
                    "completed_at": datetime.now(UTC),
                },
                action="job_failed",
                details={"reason": str(exc)},
            )

    def _log_entry(
        self,
        action: str,
        *,
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "actor": actor,
            "details": details or {},
        }

    async def _update_job(
        self,
        session: AsyncSession,
        job,
        updates: dict[str, object],
        *,
        action: str | None = None,
        actor: str = "system",
        details: dict[str, Any] | None = None,
    ):
        payload = dict(updates)
        if action:
            payload["operation_log"] = [*(job.operation_log or []), self._log_entry(action, actor=actor, details=details)]
        return await generation_jobs_repository.update(session, job, payload)

    async def _stop_job_if_timed_out(self, session: AsyncSession, job):
        timeout_seconds = self.settings.generation_job_timeout_seconds
        if timeout_seconds <= 0:
            return None

        if job.status == GenerationStatus.PENDING:
            return None

        started_at = job.started_at
        if not started_at:
            return None

        if datetime.now(UTC) < started_at + timedelta(seconds=timeout_seconds):
            return None

        try:
            await self._cancel_provider_job(job)
        except Exception as exc:
            logger.exception("Failed to stop timed out job %s", job.public_id)
            return await self._update_job(
                session,
                job,
                {
                    "status": GenerationStatus.FAILED,
                    "progress": 100,
                    "error_message": (
                        f"Generation timed out after {timeout_seconds} seconds, and auto-stop failed: {exc}"
                    ),
                    "completed_at": datetime.now(UTC),
                },
                action="job_timeout_stop_failed",
                details={"timeout_seconds": timeout_seconds, "reason": str(exc)},
            )

        return await self._update_job(
            session,
            job,
            {
                "status": GenerationStatus.FAILED,
                "progress": 100,
                "error_message": f"Generation timed out after {timeout_seconds} seconds and was stopped automatically.",
                "completed_at": datetime.now(UTC),
            },
            action="job_timed_out",
            details={"timeout_seconds": timeout_seconds},
        )

    async def _cancel_provider_job(self, job) -> None:
        if job.provider == GenerationProvider.MOCK:
            return
        if not job.external_job_id:
            return

        if job.status == GenerationStatus.QUEUED:
            await self.comfyui_client.delete_queued_prompt(job.external_job_id)
            return

        if job.status == GenerationStatus.RUNNING:
            await self.comfyui_client.interrupt_current_prompt()
            return

        if job.status == GenerationStatus.PENDING:
            return

    def _decorate_provider_payload(self, job, provider_status) -> dict[str, Any]:
        raw_payload = provider_status.raw_payload if isinstance(provider_status.raw_payload, dict) else {}
        existing_payload = job.provider_payload if isinstance(job.provider_payload, dict) else {}
        payload = {
            **{key: value for key, value in existing_payload.items() if str(key).startswith("_")},
            **dict(raw_payload),
        }
        payload["_watchdog"] = self._build_watchdog_state(job, provider_status)
        return payload

    def _build_watchdog_state(self, job, provider_status) -> dict[str, Any]:
        now = datetime.now(UTC)
        previous_payload = job.provider_payload if isinstance(job.provider_payload, dict) else {}
        previous_watchdog = previous_payload.get("_watchdog") if isinstance(previous_payload.get("_watchdog"), dict) else {}
        current_state = self._get_provider_watchdog_state(provider_status)
        previous_state = previous_watchdog.get("state")
        previous_since = previous_watchdog.get("since")

        if current_state and previous_state == current_state and isinstance(previous_since, str):
            since = previous_since
        elif current_state:
            since = now.isoformat()
        else:
            since = None

        return {
            "state": current_state,
            "since": since,
            "last_checked_at": now.isoformat(),
            "threshold_seconds": self.settings.comfyui_stalled_job_seconds,
        }

    def _get_provider_watchdog_state(self, provider_status) -> str | None:
        if provider_status.status in {GenerationStatus.COMPLETED, GenerationStatus.FAILED, GenerationStatus.CANCELLED}:
            return None
        if provider_status.in_queue_pending:
            return "queue_pending"
        if provider_status.in_queue_running:
            return "queue_running"
        return provider_status.status.value

    async def _fail_stalled_comfyui_job_if_needed(
        self,
        *,
        session: AsyncSession,
        job,
        provider_status,
        provider_payload: dict[str, Any],
    ):
        stale_seconds = self.settings.comfyui_stalled_job_seconds
        if stale_seconds <= 0:
            return None

        watchdog = provider_payload.get("_watchdog")
        if not isinstance(watchdog, dict):
            return None

        state = watchdog.get("state")
        since_raw = watchdog.get("since")
        if not isinstance(state, str) or not isinstance(since_raw, str):
            return None

        try:
            since = datetime.fromisoformat(since_raw)
        except ValueError:
            return None

        if datetime.now(UTC) < since + timedelta(seconds=stale_seconds):
            return None

        cleanup_note = ""
        if self.settings.comfyui_stalled_job_auto_interrupt:
            cleanup_note = await self._attempt_stalled_provider_cleanup(job, provider_status)

        error_message = (
            "ComfyUI generation stopped making progress and was marked as failed. "
            "If this repeats, restart ComfyUI and check its runtime log."
        )
        if cleanup_note:
            error_message = f"{error_message} {cleanup_note}"

        return await self._update_job(
            session,
            job,
            {
                "status": GenerationStatus.FAILED,
                "progress": 100,
                "error_message": error_message,
                "provider_payload": provider_payload,
                "completed_at": datetime.now(UTC),
            },
            action="provider_job_marked_stale",
            details={
                "state": state,
                "stale_seconds": stale_seconds,
                "auto_interrupt": self.settings.comfyui_stalled_job_auto_interrupt,
            },
        )

    async def _attempt_stalled_provider_cleanup(self, job, provider_status) -> str:
        try:
            if provider_status.in_queue_pending or provider_status.status == GenerationStatus.QUEUED:
                await self.comfyui_client.delete_queued_prompt(job.external_job_id)
                return "The stuck queued prompt was removed automatically."
            if provider_status.in_queue_running or provider_status.status == GenerationStatus.RUNNING:
                await self.comfyui_client.interrupt_current_prompt()
                return "The stuck running prompt was interrupted automatically."
        except Exception as exc:
            logger.exception("Failed to clean up stalled ComfyUI job %s", job.public_id)
            return f"Automatic provider cleanup failed: {exc}"
        return ""

    def _extract_visual_generation_plan(self, job) -> VisualGenerationPlan:
        provider_payload = job.provider_payload if isinstance(job.provider_payload, dict) else {}
        raw_plan = provider_payload.get("_visual_generation_plan")
        if isinstance(raw_plan, dict) and raw_plan:
            try:
                return VisualGenerationPlan.model_validate(raw_plan)
            except Exception:
                pass
        orchestration = provider_payload.get("_orchestration") if isinstance(provider_payload.get("_orchestration"), dict) else {}
        workflow_name = orchestration.get("workflow_name") if isinstance(orchestration.get("workflow_name"), str) else "fashion_flatlay_base"
        workflow_version = orchestration.get("workflow_version") if isinstance(orchestration.get("workflow_version"), str) else f"{workflow_name}.json"
        stylist = provider_payload.get("_stylist") if isinstance(provider_payload.get("_stylist"), dict) else {}
        return VisualGenerationPlan(
            mode=str(stylist.get("mode") or "general_advice"),
            style_id=stylist.get("style_id"),
            style_name=stylist.get("style_name"),
            fashion_brief_hash=stylist.get("brief_hash"),
            compiled_prompt_hash=stylist.get("compiled_prompt_hash"),
            final_prompt=job.prompt,
            negative_prompt=str(stylist.get("negative_prompt") or ""),
            visual_preset_id=stylist.get("visual_preset"),
            workflow_name=workflow_name,
            workflow_version=workflow_version,
            layout_archetype=stylist.get("layout_archetype"),
            background_family=stylist.get("background_family"),
            object_count_range=stylist.get("object_count_range"),
            spacing_density=stylist.get("spacing_density"),
            camera_distance=stylist.get("camera_distance"),
            shadow_hardness=stylist.get("shadow_hardness"),
            anchor_garment_centrality=stylist.get("anchor_garment_centrality"),
            practical_coherence=stylist.get("practical_coherence"),
            diversity_profile=stylist.get("diversity_constraints") if isinstance(stylist.get("diversity_constraints"), dict) else {},
            palette_tags=list(stylist.get("palette_tags") or []),
            garments_tags=list(stylist.get("garment_tags") or []),
            materials_tags=list(stylist.get("materials") or []),
            knowledge_refs=list(stylist.get("knowledge_refs") or []),
            metadata=dict(stylist),
        )

    def _extract_generation_metadata(self, *, job, plan: VisualGenerationPlan) -> GenerationMetadata:
        provider_payload = job.provider_payload if isinstance(job.provider_payload, dict) else {}
        raw_metadata = provider_payload.get("_generation_metadata")
        if isinstance(raw_metadata, dict) and raw_metadata:
            try:
                return GenerationMetadata.model_validate(raw_metadata)
            except Exception:
                pass
        return GenerationMetadata(
            generation_job_id=job.public_id,
            mode=plan.mode,
            style_id=plan.style_id,
            style_name=plan.style_name,
            fashion_brief_hash=plan.fashion_brief_hash,
            compiled_prompt_hash=plan.compiled_prompt_hash,
            final_prompt=plan.final_prompt,
            negative_prompt=plan.negative_prompt,
            workflow_name=plan.workflow_name,
            workflow_version=plan.workflow_version,
            visual_preset_id=plan.visual_preset_id,
            background_family=plan.background_family,
            layout_archetype=plan.layout_archetype,
            spacing_density=plan.spacing_density,
            camera_distance=plan.camera_distance,
            shadow_hardness=plan.shadow_hardness,
            anchor_garment_centrality=plan.anchor_garment_centrality,
            practical_coherence=plan.practical_coherence,
            palette_tags=list(plan.palette_tags),
            garments_tags=list(plan.garments_tags),
            materials_tags=list(plan.materials_tags),
            diversity_constraints=dict(plan.diversity_profile),
            knowledge_refs=list(plan.knowledge_refs),
        )

    def _merge_generation_metadata(
        self,
        *,
        job,
        provider_payload: dict[str, Any],
        status,
        result_url: str | None,
    ) -> dict[str, Any]:
        plan = self._extract_visual_generation_plan(job)
        metadata = self._extract_generation_metadata(job=job, plan=plan)
        metadata.generation_job_id = job.public_id
        provider_payload["_visual_generation_plan"] = plan.model_dump(mode="json")
        provider_payload["_generation_metadata"] = metadata.model_dump(mode="json")
        if result_url:
            provider_payload["_result_url"] = result_url
        provider_payload["_provider_status"] = status.value if hasattr(status, "value") else str(status)
        return provider_payload

    def _build_style_explanation(self, job) -> StyleExplanationRead | None:
        provider_payload = job.provider_payload if isinstance(job.provider_payload, dict) else {}
        raw_generation_metadata = (
            provider_payload.get("_generation_metadata")
            if isinstance(provider_payload.get("_generation_metadata"), dict)
            else {}
        )
        raw_visual_plan = (
            provider_payload.get("_visual_generation_plan")
            if isinstance(provider_payload.get("_visual_generation_plan"), dict)
            else {}
        )
        style_name = self._optional_text(
            raw_generation_metadata.get("style_name")
            or raw_visual_plan.get("style_name")
            or raw_generation_metadata.get("style_identity")
        )
        short_explanation = self._optional_text(raw_generation_metadata.get("style_explanation_short"))
        supporting_text = self._optional_text(raw_generation_metadata.get("style_explanation_supporting_text"))
        if supporting_text == short_explanation:
            supporting_text = None
        distinct_points = self._clean_string_list(raw_generation_metadata.get("style_explanation_distinct_points"))[:3]
        if not any([style_name, short_explanation, supporting_text, distinct_points]):
            return None
        return StyleExplanationRead(
            style_id=self._optional_text(raw_generation_metadata.get("style_id") or raw_visual_plan.get("style_id")),
            style_name=style_name,
            short_explanation=short_explanation,
            supporting_text=supporting_text,
            distinct_points=distinct_points,
        )

    def _log_generation_trace(
        self,
        event_name: str,
        *,
        job,
        metadata: GenerationMetadata,
        extra: dict[str, Any] | None = None,
    ) -> None:
        provider_payload = job.provider_payload if isinstance(job.provider_payload, dict) else {}
        stylist_payload = provider_payload.get("_stylist") if isinstance(provider_payload.get("_stylist"), dict) else {}
        logger.info(
            "%s | %s",
            event_name,
            {
                "session_id": job.session_id,
                "message_id": stylist_payload.get("source_message_id"),
                "mode": metadata.mode,
                "style_id": metadata.style_id,
                "fashion_brief_hash": metadata.fashion_brief_hash,
                "compiled_prompt_hash": metadata.compiled_prompt_hash,
                "workflow_name": metadata.workflow_name,
                "workflow_version": metadata.workflow_version,
                "visual_preset_id": metadata.visual_preset_id,
                "layout_archetype": metadata.layout_archetype,
                "background_family": metadata.background_family,
                "camera_distance": metadata.camera_distance,
                "spacing_density": metadata.spacing_density,
                "seed": metadata.seed,
                "generation_job_id": metadata.generation_job_id or job.public_id,
                **(extra or {}),
            },
        )

    def _build_initial_provider_payload(self, payload: GenerationJobCreate) -> dict[str, Any]:
        provider_payload: dict[str, Any] = {}
        raw_visual_generation_plan = (
            dict(payload.visual_generation_plan)
            if isinstance(payload.visual_generation_plan, dict)
            else {}
        )
        raw_generation_metadata = (
            dict(payload.generation_metadata)
            if isinstance(payload.generation_metadata, dict)
            else {}
        )
        workflow_name = (
            payload.workflow_name
            or raw_visual_generation_plan.get("workflow_name")
            or raw_generation_metadata.get("workflow_name")
        )
        workflow_version = (
            payload.workflow_version
            or raw_visual_generation_plan.get("workflow_version")
            or raw_generation_metadata.get("workflow_version")
        )
        negative_prompt = (
            payload.negative_prompt
            or raw_visual_generation_plan.get("negative_prompt")
            or raw_generation_metadata.get("negative_prompt")
        )
        stylist_payload = dict(payload.metadata) if isinstance(payload.metadata, dict) else {}
        if negative_prompt and "negative_prompt" not in stylist_payload:
            stylist_payload["negative_prompt"] = negative_prompt
        if workflow_name and "workflow_name" not in stylist_payload:
            stylist_payload["workflow_name"] = workflow_name
        if workflow_version and "workflow_version" not in stylist_payload:
            stylist_payload["workflow_version"] = workflow_version
        if stylist_payload:
            provider_payload["_stylist"] = stylist_payload
        if raw_visual_generation_plan:
            provider_payload["_visual_generation_plan"] = raw_visual_generation_plan
        if raw_generation_metadata:
            provider_payload["_generation_metadata"] = raw_generation_metadata
        orchestration: dict[str, Any] = {}
        if payload.idempotency_key:
            orchestration["idempotency_key"] = payload.idempotency_key
        if workflow_name:
            orchestration["workflow_name"] = workflow_name
        if workflow_version:
            orchestration["workflow_version"] = workflow_version
        if orchestration:
            provider_payload["_orchestration"] = orchestration
        return provider_payload

    def _optional_text(self, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip()
        return cleaned or None

    def _clean_string_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _queue_refresh_key(self, public_id: str) -> str:
        return f"{self.QUEUE_REFRESH_KEY_PREFIX}{public_id}"

    async def _get_queue_refresh_window(self, public_id: str) -> tuple[datetime | None, int | None]:
        cooldown_seconds = max(self.settings.generation_queue_refresh_cooldown_seconds, 0)
        if cooldown_seconds <= 0:
            return None, None

        try:
            raw_timestamp = await self.redis.get(self._queue_refresh_key(public_id))
        except Exception:
            logger.exception("Failed to read generation queue refresh cooldown from Redis")
            return None, None

        if not raw_timestamp:
            return None, None

        try:
            last_refresh_at = datetime.fromisoformat(raw_timestamp)
        except ValueError:
            return None, None

        next_available_at = last_refresh_at + timedelta(seconds=cooldown_seconds)
        retry_after_seconds = max(0, int((next_available_at - datetime.now(UTC)).total_seconds()))
        if retry_after_seconds <= 0:
            return None, None
        return next_available_at, retry_after_seconds

    async def _enforce_queue_refresh_cooldown(self, public_id: str) -> None:
        next_available_at, retry_after_seconds = await self._get_queue_refresh_window(public_id)
        if retry_after_seconds:
            raise QueueRefreshCooldownError(
                retry_after_seconds=retry_after_seconds,
                next_available_at=next_available_at or datetime.now(UTC),
            )

        cooldown_seconds = max(self.settings.generation_queue_refresh_cooldown_seconds, 0)
        if cooldown_seconds <= 0:
            return

        try:
            await self.redis.set(
                self._queue_refresh_key(public_id),
                datetime.now(UTC).isoformat(),
                ex=cooldown_seconds,
            )
        except Exception:
            logger.exception("Failed to write generation queue refresh cooldown to Redis")


generation_service = GenerationService()
