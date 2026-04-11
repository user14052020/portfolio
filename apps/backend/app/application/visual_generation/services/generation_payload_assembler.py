from app.application.visual_generation.contracts import WorkflowSelection
from app.domain.prompt_building.entities.compiled_image_prompt import CompiledImagePrompt
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan, VisualPreset


class GenerationPayloadAssembler:
    async def assemble(
        self,
        *,
        fashion_brief: FashionBrief,
        compiled_prompt: CompiledImagePrompt,
        visual_preset: VisualPreset,
        workflow_selection: WorkflowSelection,
    ) -> tuple[VisualGenerationPlan, GenerationMetadata]:
        metadata = dict(fashion_brief.metadata)
        plan = VisualGenerationPlan(
            mode=fashion_brief.brief_mode,
            style_id=metadata.get("style_id"),
            style_name=fashion_brief.style_identity,
            fashion_brief_hash=fashion_brief.content_hash(),
            compiled_prompt_hash=compiled_prompt.content_hash(),
            final_prompt=compiled_prompt.final_prompt,
            negative_prompt=compiled_prompt.negative_prompt,
            visual_preset_id=visual_preset.id,
            workflow_name=workflow_selection.workflow_name,
            workflow_version=workflow_selection.workflow_version,
            layout_archetype=visual_preset.layout_archetype,
            background_family=visual_preset.background_family,
            object_count_range=visual_preset.object_count_range,
            spacing_density=visual_preset.spacing_density,
            camera_distance=visual_preset.camera_distance,
            shadow_hardness=visual_preset.shadow_hardness,
            anchor_garment_centrality=visual_preset.anchor_garment_centrality,
            practical_coherence=visual_preset.practical_coherence,
            diversity_profile=dict(fashion_brief.diversity_constraints),
            palette_tags=list(compiled_prompt.palette_tags),
            garments_tags=list(compiled_prompt.garment_tags),
            materials_tags=list(fashion_brief.materials),
            knowledge_refs=list(metadata.get("knowledge_refs") or []),
            metadata={
                "style_family": fashion_brief.style_family,
                "historical_reference": list(fashion_brief.historical_reference),
                "garment_list": list(fashion_brief.garment_list),
                "composition_rules": list(fashion_brief.composition_rules),
                "knowledge_bundle_hash": metadata.get("knowledge_bundle_hash"),
                "knowledge_query_hash": metadata.get("knowledge_query_hash"),
                "retrieved_style_cards_count": metadata.get("retrieved_style_cards_count"),
                "retrieved_color_cards_count": metadata.get("retrieved_color_cards_count"),
                "retrieved_history_cards_count": metadata.get("retrieved_history_cards_count"),
                "retrieved_tailoring_cards_count": metadata.get("retrieved_tailoring_cards_count"),
                "retrieved_material_cards_count": metadata.get("retrieved_material_cards_count"),
                "retrieved_flatlay_cards_count": metadata.get("retrieved_flatlay_cards_count"),
                "anti_repeat_constraints": metadata.get("anti_repeat_constraints") or {},
            },
        )
        generation_metadata = GenerationMetadata(
            mode=fashion_brief.brief_mode,
            style_id=plan.style_id,
            style_name=plan.style_name,
            fashion_brief_hash=plan.fashion_brief_hash,
            compiled_prompt_hash=plan.compiled_prompt_hash,
            final_prompt=plan.final_prompt,
            negative_prompt=plan.negative_prompt,
            workflow_name=plan.workflow_name,
            workflow_version=plan.workflow_version,
            visual_preset_id=plan.visual_preset_id,
            background_family=plan.background_family,
            layout_archetype=plan.layout_archetype,
            spacing_density=plan.spacing_density,
            camera_distance=plan.camera_distance,
            shadow_hardness=plan.shadow_hardness,
            anchor_garment_centrality=plan.anchor_garment_centrality,
            practical_coherence=plan.practical_coherence,
            palette_tags=list(plan.palette_tags),
            garments_tags=list(plan.garments_tags),
            materials_tags=list(plan.materials_tags),
            diversity_constraints=dict(plan.diversity_profile),
            knowledge_refs=list(plan.knowledge_refs),
        )
        return plan, generation_metadata

