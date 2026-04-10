from pydantic import BaseModel, Field

from app.domain.occasion_outfit.entities.occasion_context import OccasionContext
from app.domain.occasion_outfit.enums.occasion_slot import OccasionSlot


class OccasionCompletenessAssessment(BaseModel):
    missing_slots: list[str] = Field(default_factory=list)
    filled_slots: list[str] = Field(default_factory=list)
    clarification_slot: OccasionSlot | None = None
    completeness_score: float = 0.0
    is_sufficient_for_generation: bool = False


class OccasionCompletenessPolicy:
    def evaluate(self, context: OccasionContext) -> OccasionCompletenessAssessment:
        filled_slots = context.filled_slots()
        missing_slots = context.missing_core_slots()

        score = 0.0
        score += 0.28 if context.event_type else 0.0
        score += 0.22 if context.time_of_day else 0.0
        score += 0.22 if context.season else 0.0
        score += 0.18 if context.dress_code or context.desired_impression else 0.0
        score += 0.05 if context.location else 0.0
        score += 0.05 if context.weather_context else 0.0
        score += 0.03 if context.constraints else 0.0
        score += 0.03 if context.color_preferences or context.garment_preferences else 0.0

        clarification_slot: OccasionSlot | None = None
        if OccasionSlot.EVENT_TYPE.value in missing_slots:
            clarification_slot = OccasionSlot.EVENT_TYPE
        elif OccasionSlot.TIME_OF_DAY.value in missing_slots:
            clarification_slot = OccasionSlot.TIME_OF_DAY
        elif OccasionSlot.SEASON.value in missing_slots:
            clarification_slot = OccasionSlot.SEASON
        elif (
            OccasionSlot.DRESS_CODE.value in missing_slots
            and OccasionSlot.DESIRED_IMPRESSION.value in missing_slots
        ):
            clarification_slot = OccasionSlot.DRESS_CODE

        return OccasionCompletenessAssessment(
            missing_slots=missing_slots,
            filled_slots=filled_slots,
            clarification_slot=clarification_slot,
            completeness_score=min(score, 1.0),
            is_sufficient_for_generation=not bool(missing_slots),
        )
