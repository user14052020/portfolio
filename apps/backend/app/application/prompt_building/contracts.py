from typing import Protocol

from app.domain.prompt_building.entities.compiled_image_prompt import CompiledImagePrompt
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.prompt_building.entities.generation_payload import GenerationPayload
from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan


class FashionReasoner(Protocol):
    async def build_brief(self, *, reasoning_input) -> FashionBrief:
        ...


class FashionBriefRepository(Protocol):
    async def save(self, *, brief: FashionBrief) -> None:
        ...


class PromptCompiler(Protocol):
    async def compile(self, *, brief: FashionBrief) -> CompiledImagePrompt:
        ...


class PromptValidator(Protocol):
    async def validate_brief(self, brief: FashionBrief) -> list[str]:
        ...

    async def validate_compiled(self, prompt: CompiledImagePrompt) -> list[str]:
        ...


class GenerationPayloadAdapter(Protocol):
    async def adapt(
        self,
        *,
        plan: VisualGenerationPlan,
        metadata: GenerationMetadata,
    ) -> GenerationPayload:
        ...
