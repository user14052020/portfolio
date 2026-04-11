from app.application.visual_generation.services.generation_metadata_recorder import GenerationMetadataRecorder
from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan


class PersistGenerationResultUseCase:
    def __init__(self, *, generation_metadata_recorder: GenerationMetadataRecorder) -> None:
        self.generation_metadata_recorder = generation_metadata_recorder

    async def execute(
        self,
        *,
        job,
        plan: VisualGenerationPlan,
        metadata: GenerationMetadata,
    ):
        return await self.generation_metadata_recorder.record_for_job(
            job=job,
            plan=plan,
            metadata=metadata,
        )

