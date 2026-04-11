from app.application.visual_generation.contracts import (
    GenerationPayloadAssemblerPort,
    VisualPresetResolverPort,
    WorkflowSelectorPort,
)
from app.domain.prompt_building.entities.compiled_image_prompt import CompiledImagePrompt
from app.domain.prompt_building.entities.fashion_brief import FashionBrief


class BuildVisualGenerationPlanUseCase:
    def __init__(
        self,
        *,
        visual_preset_resolver: VisualPresetResolverPort,
        workflow_selector: WorkflowSelectorPort,
        generation_payload_assembler: GenerationPayloadAssemblerPort,
    ) -> None:
        self.visual_preset_resolver = visual_preset_resolver
        self.workflow_selector = workflow_selector
        self.generation_payload_assembler = generation_payload_assembler

    async def execute(
        self,
        *,
        fashion_brief: FashionBrief,
        compiled_prompt: CompiledImagePrompt,
    ):
        visual_preset = await self.visual_preset_resolver.resolve(
            mode=fashion_brief.brief_mode,
            fashion_brief=fashion_brief,
            style_history=fashion_brief.metadata.get("previous_style_directions") or [],
            diversity_constraints=fashion_brief.diversity_constraints,
        )
        workflow_selection = await self.workflow_selector.select(
            mode=fashion_brief.brief_mode,
            visual_preset=visual_preset,
            fashion_brief=fashion_brief,
        )
        return await self.generation_payload_assembler.assemble(
            fashion_brief=fashion_brief,
            compiled_prompt=compiled_prompt,
            visual_preset=visual_preset,
            workflow_selection=workflow_selection,
        )

