from app.application.visual_generation.contracts import GenerationBackendAdapter
from app.domain.visual_generation import VisualGenerationPlan


class RunGenerationJobUseCase:
    def __init__(self, *, generation_backend_adapter: GenerationBackendAdapter) -> None:
        self.generation_backend_adapter = generation_backend_adapter

    async def execute(
        self,
        *,
        plan: VisualGenerationPlan,
        input_image_url: str | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
    ):
        return await self.generation_backend_adapter.prepare_run(
            plan=plan,
            input_image_url=input_image_url,
            body_height_cm=body_height_cm,
            body_weight_kg=body_weight_kg,
        )

