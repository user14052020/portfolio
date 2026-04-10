from app.domain.chat_modes import ClarificationKind
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment
from app.domain.garment_matching.policies.garment_clarification_policy import GarmentClarificationPolicy
from app.domain.garment_matching.policies.garment_completeness_policy import GarmentCompletenessAssessment


class GarmentClarificationService:
    def __init__(self, policy: GarmentClarificationPolicy | None = None) -> None:
        self.policy = policy or GarmentClarificationPolicy()

    def build(
        self,
        *,
        locale: str,
        garment: AnchorGarment,
        assessment: GarmentCompletenessAssessment,
    ) -> tuple[ClarificationKind, str]:
        return self.policy.build(locale=locale, garment=garment, assessment=assessment)
