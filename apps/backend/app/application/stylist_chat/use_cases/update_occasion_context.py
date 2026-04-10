from app.application.stylist_chat.contracts.ports import OccasionCompletenessEvaluator
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessAssessment


class UpdateOccasionContextUseCase:
    def __init__(self, *, completeness_evaluator: OccasionCompletenessEvaluator) -> None:
        self.completeness_evaluator = completeness_evaluator

    def execute(self, *, occasion_context: OccasionContext) -> OccasionCompletenessAssessment:
        assessment = self.completeness_evaluator.evaluate(occasion_context)
        occasion_context.completeness_score = assessment.completeness_score
        occasion_context.is_sufficient_for_generation = assessment.is_sufficient_for_generation
        return assessment
