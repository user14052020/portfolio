from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan
from app.repositories.generation_jobs import generation_jobs_repository


class GenerationJobMetadataStore:
    def __init__(self, session) -> None:
        self.session = session

    async def save_for_job(self, *, job, plan: VisualGenerationPlan, metadata: GenerationMetadata):
        provider_payload = job.provider_payload if isinstance(job.provider_payload, dict) else {}
        return await generation_jobs_repository.update(
            self.session,
            job,
            {
                "provider_payload": {
                    **provider_payload,
                    "_visual_generation_plan": plan.model_dump(mode="json"),
                    "_generation_metadata": metadata.model_dump(mode="json"),
                }
            },
        )

