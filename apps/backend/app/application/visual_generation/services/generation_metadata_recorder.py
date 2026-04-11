from app.application.visual_generation.contracts import GenerationMetadataStore
from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan


class GenerationMetadataRecorder:
    def __init__(self, *, store: GenerationMetadataStore) -> None:
        self.store = store

    async def record_for_job(
        self,
        *,
        job,
        plan: VisualGenerationPlan,
        metadata: GenerationMetadata,
    ):
        return await self.store.save_for_job(job=job, plan=plan, metadata=metadata)

