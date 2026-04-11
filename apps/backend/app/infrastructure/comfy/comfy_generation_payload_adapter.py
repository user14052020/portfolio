from pathlib import Path

from pydantic import ValidationError

from app.core.config import get_settings
from app.domain.prompt_building.entities.generation_payload import GenerationPayload as PromptGenerationPayload
from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan


DEFAULT_COMFY_WORKFLOW_TEMPLATE = Path("app/infrastructure/comfy/workflows/fashion_flatlay_base.json")


def _resolve_workflow_template_path() -> Path:
    try:
        return Path(get_settings().comfyui_workflow_template)
    except (ValidationError, OSError, RuntimeError):
        return DEFAULT_COMFY_WORKFLOW_TEMPLATE


class ComfyGenerationPayloadAdapter:
    def __init__(
        self,
        *,
        workflow_template_path: str | Path | None = None,
        positive_prompt_field: str = "__PROMPT__",
        negative_prompt_supported: bool = False,
    ) -> None:
        self.template_path = (
            Path(workflow_template_path) if workflow_template_path is not None else _resolve_workflow_template_path()
        )
        self.positive_prompt_field = positive_prompt_field
        self.negative_prompt_supported = negative_prompt_supported

    async def adapt(
        self,
        *,
        plan: VisualGenerationPlan,
        metadata: GenerationMetadata,
    ) -> PromptGenerationPayload:
        return PromptGenerationPayload(
            workflow_name=plan.workflow_name,
            workflow_version=plan.workflow_version or self.template_path.name,
            prompt=plan.final_prompt,
            negative_prompt=plan.negative_prompt,
            visual_preset=plan.visual_preset_id,
            metadata={
                **plan.metadata,
                "workflow_name": plan.workflow_name,
                "workflow_version": plan.workflow_version or self.template_path.name,
                "negative_prompt": plan.negative_prompt,
                "visual_preset": plan.visual_preset_id,
                "workflow_bindings": {
                    "positive_prompt_field": self.positive_prompt_field,
                    "negative_prompt_supported": self.negative_prompt_supported,
                },
            },
            visual_generation_plan=plan,
            generation_metadata=metadata,
        )
