from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints
from app.domain.style_exploration.entities.style_direction import StyleDirection


class BuildDiversityConstraintsUseCase:
    def __init__(self, *, semantic_diversity_builder, visual_diversity_builder) -> None:
        self.semantic_diversity_builder = semantic_diversity_builder
        self.visual_diversity_builder = visual_diversity_builder

    def execute(
        self,
        *,
        history: list[StyleDirection],
        candidate_style: StyleDirection,
        session_context: dict | None = None,
    ) -> DiversityConstraints:
        semantic = self.semantic_diversity_builder.build(
            history=history,
            candidate_style=candidate_style,
            session_context=session_context,
        )
        visual = self.visual_diversity_builder.build(
            history=history,
            current_visual_presets=[
                {
                    "visual_preset": candidate_style.visual_preset,
                    "composition_type": candidate_style.composition_type,
                    "background_family": candidate_style.background_family,
                }
            ],
        )
        merged = semantic.model_copy(deep=True)
        merged.avoid_composition_types = visual.avoid_composition_types
        merged.avoid_background_families = visual.avoid_background_families
        merged.avoid_layout_density = visual.avoid_layout_density
        merged.avoid_camera_distance = visual.avoid_camera_distance
        merged.force_visual_preset_shift = visual.force_visual_preset_shift
        merged.target_visual_distance = visual.target_visual_distance
        merged.suggested_visual_preset = visual.suggested_visual_preset
        return merged
