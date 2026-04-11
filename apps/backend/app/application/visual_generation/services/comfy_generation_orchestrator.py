from dataclasses import dataclass
from typing import Any

from app.application.visual_generation.contracts import PreparedGenerationRun
from app.application.visual_generation.use_cases.persist_generation_result import PersistGenerationResultUseCase
from app.application.visual_generation.use_cases.run_generation_job import RunGenerationJobUseCase
from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan


@dataclass(slots=True)
class ComfyGenerationOrchestrationResult:
    job: Any
    prepared_run: PreparedGenerationRun
    plan: VisualGenerationPlan
    metadata: GenerationMetadata


class ComfyGenerationOrchestrator:
    def __init__(
        self,
        *,
        run_generation_job: RunGenerationJobUseCase,
        persist_generation_result: PersistGenerationResultUseCase,
    ) -> None:
        self.run_generation_job = run_generation_job
        self.persist_generation_result = persist_generation_result

    async def prepare_generation(
        self,
        *,
        job,
        plan: VisualGenerationPlan,
        metadata: GenerationMetadata,
        input_image_url: str | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
    ) -> ComfyGenerationOrchestrationResult:
        prepared_run = await self.run_generation_job.execute(
            plan=plan,
            input_image_url=input_image_url,
            body_height_cm=body_height_cm,
            body_weight_kg=body_weight_kg,
        )
        resolved_plan = plan.model_copy(
            update={
                "workflow_name": prepared_run.workflow_name,
                "workflow_version": prepared_run.workflow_version,
            }
        )
        resolved_metadata = metadata.model_copy(
            update={
                "generation_job_id": job.public_id,
                "seed": prepared_run.seed,
                "workflow_name": prepared_run.workflow_name,
                "workflow_version": prepared_run.workflow_version,
            }
        )
        persisted_job = await self.persist_generation_result.execute(
            job=job,
            plan=resolved_plan,
            metadata=resolved_metadata,
        )
        return ComfyGenerationOrchestrationResult(
            job=persisted_job,
            prepared_run=prepared_run,
            plan=resolved_plan,
            metadata=resolved_metadata,
        )
