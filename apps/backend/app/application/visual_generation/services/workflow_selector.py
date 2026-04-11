from app.application.visual_generation.contracts import WorkflowSelection
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.visual_generation import VisualPreset
from app.infrastructure.comfy.workflows.registry import get_workflow_template


class ComfyWorkflowSelector:
    async def select(
        self,
        mode: str,
        visual_preset: VisualPreset,
        fashion_brief: FashionBrief,
    ) -> WorkflowSelection:
        if mode == "garment_matching" or visual_preset.anchor_garment_centrality == "high":
            workflow_name = "garment_matching_variation"
        elif mode == "occasion_outfit" or visual_preset.practical_coherence == "high":
            workflow_name = "occasion_outfit_variation"
        elif mode == "style_exploration" or visual_preset.diversity_bias == "high":
            workflow_name = "style_exploration_variation"
        else:
            workflow_name = "fashion_flatlay_base"

        template_path = get_workflow_template(workflow_name)
        return WorkflowSelection(
            workflow_name=workflow_name,
            workflow_version=template_path.name,
            template_path=str(template_path),
        )

