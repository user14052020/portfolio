from app.application.visual_generation.contracts import PreparedGenerationRun
from app.domain.visual_generation import VisualGenerationPlan
from app.infrastructure.comfy.client.comfy_client import ComfyClient


class ComfyGenerationAdapter:
    def __init__(self, *, client: ComfyClient | None = None) -> None:
        self.client = client or ComfyClient()

    async def prepare_run(
        self,
        *,
        plan: VisualGenerationPlan,
        input_image_url: str | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
    ) -> PreparedGenerationRun:
        return await self.client.prepare_run(
            plan=plan,
            input_image_url=input_image_url,
            body_height_cm=body_height_cm,
            body_weight_kg=body_weight_kg,
        )

    async def submit(self, *, workflow_payload: dict) -> str:
        return await self.client.submit(workflow_payload=workflow_payload)

