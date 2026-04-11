from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints
from app.domain.style_exploration.entities.style_direction import StyleDirection
from app.domain.style_exploration.policies.semantic_diversity_policy import SemanticDiversityPolicy


class SemanticDiversityService:
    def __init__(self, policy: SemanticDiversityPolicy) -> None:
        self.policy = policy

    def build(
        self,
        *,
        history: list[StyleDirection],
        candidate_style: StyleDirection,
        session_context: dict | None = None,
    ) -> DiversityConstraints:
        return self.policy.build(
            history=history,
            candidate_style=candidate_style,
            session_context=session_context,
        )
