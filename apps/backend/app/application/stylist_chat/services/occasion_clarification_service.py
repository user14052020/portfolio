from app.domain.chat_modes import ClarificationKind
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext
from app.domain.occasion_outfit.policies.occasion_clarification_policy import OccasionClarificationPolicy
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessAssessment


class OccasionClarificationService:
    def __init__(self, policy: OccasionClarificationPolicy | None = None) -> None:
        self.policy = policy or OccasionClarificationPolicy()

    def build(
        self,
        *,
        locale: str,
        context: OccasionContext,
        assessment: OccasionCompletenessAssessment,
    ) -> tuple[ClarificationKind, str]:
        return self.policy.build(locale=locale, context=context, assessment=assessment)
