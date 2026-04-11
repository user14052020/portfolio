from typing import Any

from pydantic import BaseModel, Field

from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan


class GenerationPayload(BaseModel):
    workflow_name: str
    workflow_version: str
    prompt: str
    negative_prompt: str
    visual_preset: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    visual_generation_plan: VisualGenerationPlan | None = None
    generation_metadata: GenerationMetadata | None = None
