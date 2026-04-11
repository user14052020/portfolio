from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints
from app.domain.style_exploration.entities.style_direction import StyleDirection
from app.domain.style_exploration.policies.visual_diversity_policy import VisualDiversityPolicy


class VisualDiversityService:
    def __init__(self, policy: VisualDiversityPolicy) -> None:
        self.policy = policy

    def build(
        self,
        *,
        history: list[StyleDirection],
        current_visual_presets: list[dict] | None = None,
    ) -> DiversityConstraints:
        return self.policy.build(
            history=history,
            current_visual_presets=current_visual_presets,
        )
