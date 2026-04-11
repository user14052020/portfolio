from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.prompt_building.entities.compiled_image_prompt import CompiledImagePrompt
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan, VisualPreset


@dataclass(slots=True)
class WorkflowSelection:
    workflow_name: str
    workflow_version: str
    template_path: str


@dataclass(slots=True)
class PreparedGenerationRun:
    workflow_payload: dict[str, Any]
    seed: int | None
    workflow_name: str
    workflow_version: str | None


class VisualPresetResolverPort(Protocol):
    async def resolve(
        self,
        mode: str,
        fashion_brief: FashionBrief,
        style_history: list[dict[str, Any]] | None = None,
        diversity_constraints: dict[str, Any] | None = None,
    ) -> VisualPreset:
        ...


class WorkflowSelectorPort(Protocol):
    async def select(
        self,
        mode: str,
        visual_preset: VisualPreset,
        fashion_brief: FashionBrief,
    ) -> WorkflowSelection:
        ...


class GenerationPayloadAssemblerPort(Protocol):
    async def assemble(
        self,
        *,
        fashion_brief: FashionBrief,
        compiled_prompt: CompiledImagePrompt,
        visual_preset: VisualPreset,
        workflow_selection: WorkflowSelection,
    ) -> tuple[VisualGenerationPlan, GenerationMetadata]:
        ...


class GenerationBackendAdapter(Protocol):
    async def prepare_run(
        self,
        *,
        plan: VisualGenerationPlan,
        input_image_url: str | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
    ) -> PreparedGenerationRun:
        ...

    async def submit(self, *, workflow_payload: dict[str, Any]) -> str:
        ...


class GenerationMetadataStore(Protocol):
    async def save_for_job(self, *, job, plan: VisualGenerationPlan, metadata: GenerationMetadata) -> Any:
        ...

