from app.application.stylist_chat.services.style_exploration_context_builder import StyleExplorationContextBuilder
from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints
from app.domain.style_exploration.entities.style_direction import StyleDirection
from app.domain.style_exploration.entities.style_exploration_brief import StyleExplorationBrief


class BuildStyleExplorationBriefUseCase:
    def __init__(self, *, context_builder: StyleExplorationContextBuilder) -> None:
        self.context_builder = context_builder

    async def execute(
        self,
        *,
        style_direction: StyleDirection,
        history: list[StyleDirection],
        diversity_constraints: DiversityConstraints,
    ) -> StyleExplorationBrief:
        context = self.context_builder.build(
            style_direction=style_direction,
            history=history,
        )
        effective_visual_preset = (
            diversity_constraints.suggested_visual_preset
            if diversity_constraints.force_visual_preset_shift and diversity_constraints.suggested_visual_preset
            else style_direction.visual_preset or diversity_constraints.suggested_visual_preset
        )
        resolved_style_direction = style_direction.model_copy(
            update={"visual_preset": effective_visual_preset}
        )
        style_identity = style_direction.style_name or "Style Direction"
        summary_bits = [
            style_identity,
            ", ".join(style_direction.palette[:3]),
            style_direction.silhouette_family or "",
            ", ".join(style_direction.hero_garments[:2]),
        ]
        negative_constraints = []
        if diversity_constraints.avoid_palette:
            negative_constraints.append(f"avoid palette: {', '.join(diversity_constraints.avoid_palette[:4])}")
        if diversity_constraints.avoid_hero_garments:
            negative_constraints.append(
                f"avoid hero garments: {', '.join(diversity_constraints.avoid_hero_garments[:4])}"
            )
        if diversity_constraints.avoid_silhouette_families:
            negative_constraints.append(
                "avoid silhouette families: "
                + ", ".join(diversity_constraints.avoid_silhouette_families[:3])
            )
        if diversity_constraints.avoid_materials:
            negative_constraints.append(
                f"avoid materials: {', '.join(diversity_constraints.avoid_materials[:4])}"
            )
        if diversity_constraints.avoid_footwear:
            negative_constraints.append(
                f"avoid footwear: {', '.join(diversity_constraints.avoid_footwear[:3])}"
            )
        if diversity_constraints.avoid_accessories:
            negative_constraints.append(
                f"avoid accessories: {', '.join(diversity_constraints.avoid_accessories[:3])}"
            )
        if diversity_constraints.avoid_composition_types:
            negative_constraints.append(
                f"avoid composition: {', '.join(diversity_constraints.avoid_composition_types[:2])}"
            )
        if diversity_constraints.avoid_background_families:
            negative_constraints.append(
                f"avoid background: {', '.join(diversity_constraints.avoid_background_families[:2])}"
            )
        if diversity_constraints.avoid_layout_density:
            negative_constraints.append(
                f"avoid layout density: {', '.join(diversity_constraints.avoid_layout_density[:2])}"
            )
        if diversity_constraints.avoid_camera_distance:
            negative_constraints.append(
                f"avoid camera distance: {', '.join(diversity_constraints.avoid_camera_distance[:2])}"
            )
        composition_rules = []
        if style_direction.composition_type:
            composition_rules.append(f"use {style_direction.composition_type}")
        if style_direction.background_family:
            composition_rules.append(f"on {style_direction.background_family} surface")
        if style_direction.layout_density:
            composition_rules.append(f"{style_direction.layout_density} layout density")
        if style_direction.camera_distance:
            composition_rules.append(f"{style_direction.camera_distance} camera distance")
        if diversity_constraints.force_material_contrast:
            composition_rules.append("force visible material contrast against the recent history")
        if diversity_constraints.force_footwear_change:
            composition_rules.append("change the footwear family versus the recent history")
        if diversity_constraints.force_accessory_change:
            composition_rules.append("change the accessory logic versus the recent history")
        if diversity_constraints.suggested_visual_preset:
            composition_rules.append(f"shift to {diversity_constraints.suggested_visual_preset} visual preset")
        return StyleExplorationBrief(
            style_identity=style_identity,
            style_family=style_direction.style_family,
            style_summary="; ".join(bit for bit in summary_bits if bit),
            historical_reference=[style_identity],
            tailoring_logic=[style_direction.silhouette_family] if style_direction.silhouette_family else [],
            color_logic=[
                f"keep focus on {', '.join(style_direction.palette[:3])}"
            ]
            if style_direction.palette
            else [],
            garment_list=list(style_direction.hero_garments),
            palette=list(style_direction.palette),
            materials=list(style_direction.materials),
            footwear=list(style_direction.footwear),
            accessories=list(style_direction.accessories),
            styling_notes=list(style_direction.styling_mood),
            composition_rules=composition_rules,
            negative_constraints=negative_constraints,
            diversity_constraints=diversity_constraints,
            selected_style_direction=resolved_style_direction,
            visual_preset=effective_visual_preset,
            composition_type=style_direction.composition_type,
            background_family=style_direction.background_family,
            semantic_constraints_hash=diversity_constraints.semantic_hash(),
            visual_constraints_hash=diversity_constraints.visual_hash(),
            diversity_constraints_hash=diversity_constraints.combined_hash(),
        )
