from app.application.visual_generation.services.generation_payload_assembler import GenerationPayloadAssembler
from app.application.visual_generation.services.visual_preset_resolver import VisualPresetResolver
from app.application.visual_generation.services.workflow_selector import ComfyWorkflowSelector
from app.application.visual_generation.use_cases.build_visual_generation_plan import BuildVisualGenerationPlanUseCase
from app.domain.prompt_building.entities.compiled_image_prompt import CompiledImagePrompt
from app.domain.prompt_building.entities.fashion_brief import FashionBrief


class GenerationPayloadBuilder:
    def __init__(self, *, payload_adapter) -> None:
        self.payload_adapter = payload_adapter
        self.build_visual_generation_plan = BuildVisualGenerationPlanUseCase(
            visual_preset_resolver=VisualPresetResolver(),
            workflow_selector=ComfyWorkflowSelector(),
            generation_payload_assembler=GenerationPayloadAssembler(),
        )

    async def build(
        self,
        *,
        fashion_brief: FashionBrief,
        compiled_prompt: CompiledImagePrompt,
        validation_errors: list[str],
    ):
        visual_plan, generation_metadata = await self.build_visual_generation_plan.execute(
            fashion_brief=fashion_brief,
            compiled_prompt=compiled_prompt,
        )
        payload = await self.payload_adapter.adapt(
            plan=visual_plan,
            metadata=generation_metadata,
        )
        metadata = {
            **payload.metadata,
            "fashion_brief": fashion_brief.model_dump(mode="json"),
            "compiled_image_prompt": compiled_prompt.model_dump(mode="json"),
            "chosen_visual_preset": visual_plan.visual_preset_id,
            "mode": fashion_brief.brief_mode,
            "style_metadata": {
                "style_id": fashion_brief.metadata.get("style_id"),
                "source_style_id": fashion_brief.metadata.get("source_style_id"),
                "style_identity": fashion_brief.style_identity,
                "style_family": fashion_brief.style_family,
            },
            "palette_tags": visual_plan.palette_tags,
            "garment_tags": visual_plan.garments_tags,
            "materials_tags": visual_plan.materials_tags,
            "style_tags": compiled_prompt.style_tags,
            "composition_tags": compiled_prompt.composition_tags,
            "diversity_constraints": fashion_brief.diversity_constraints,
            "brief_hash": fashion_brief.content_hash(),
            "compiled_prompt_hash": compiled_prompt.content_hash(),
            "knowledge_cards_count": len(fashion_brief.knowledge_cards),
            "knowledge_bundle_hash": fashion_brief.metadata.get("knowledge_bundle_hash"),
            "knowledge_query_hash": fashion_brief.metadata.get("knowledge_query_hash"),
            "validation_errors": list(validation_errors),
            "validation_errors_count": len(validation_errors),
            "retrieved_style_cards_count": fashion_brief.metadata.get("retrieved_style_cards_count"),
            "retrieved_color_cards_count": fashion_brief.metadata.get("retrieved_color_cards_count"),
            "retrieved_history_cards_count": fashion_brief.metadata.get("retrieved_history_cards_count"),
            "retrieved_tailoring_cards_count": fashion_brief.metadata.get("retrieved_tailoring_cards_count"),
            "retrieved_material_cards_count": fashion_brief.metadata.get("retrieved_material_cards_count"),
            "retrieved_flatlay_cards_count": fashion_brief.metadata.get("retrieved_flatlay_cards_count"),
            "knowledge_refs": fashion_brief.metadata.get("knowledge_refs") or [],
            "style_id": fashion_brief.metadata.get("style_id"),
            "source_style_id": fashion_brief.metadata.get("source_style_id"),
            "style_name": fashion_brief.style_identity,
            "palette": visual_plan.palette_tags,
            "materials": visual_plan.materials_tags,
            "footwear": fashion_brief.footwear,
            "accessories": fashion_brief.accessories,
            "visual_preset": visual_plan.visual_preset_id,
            "workflow_name": visual_plan.workflow_name,
            "workflow_version": visual_plan.workflow_version,
            "layout_archetype": visual_plan.layout_archetype,
            "background_family": visual_plan.background_family,
            "object_count_range": visual_plan.object_count_range,
            "spacing_density": visual_plan.spacing_density,
            "camera_distance": visual_plan.camera_distance,
            "shadow_hardness": visual_plan.shadow_hardness,
            "anchor_garment_centrality": visual_plan.anchor_garment_centrality,
            "practical_coherence": visual_plan.practical_coherence,
            "semantic_constraints_hash": fashion_brief.metadata.get("semantic_constraints_hash"),
            "visual_constraints_hash": fashion_brief.metadata.get("visual_constraints_hash"),
            "diversity_constraints_hash": fashion_brief.metadata.get("diversity_constraints_hash"),
            "previous_style_directions": fashion_brief.metadata.get("previous_style_directions") or [],
            "anti_repeat_constraints": fashion_brief.metadata.get("anti_repeat_constraints") or {},
            "visual_generation_plan": visual_plan.model_dump(mode="json"),
            "generation_metadata": generation_metadata.model_dump(mode="json"),
        }
        return payload.model_copy(
            update={
                "metadata": metadata,
                "visual_generation_plan": visual_plan,
                "generation_metadata": generation_metadata,
            }
        )
