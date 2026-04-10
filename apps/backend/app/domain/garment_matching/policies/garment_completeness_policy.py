from pydantic import BaseModel, Field

from app.domain.garment_matching.entities.anchor_garment import AnchorGarment


class GarmentCompletenessAssessment(BaseModel):
    missing_fields: list[str] = Field(default_factory=list)
    clarification_focus: str | None = None
    completeness_score: float = 0.0
    is_sufficient_for_generation: bool = False


class GarmentCompletenessPolicy:
    def evaluate(self, garment: AnchorGarment) -> GarmentCompletenessAssessment:
        has_descriptor = bool(garment.color_primary or garment.material)
        has_styling_context = bool(garment.formality or garment.seasonality or garment.style_hints or garment.asset_id)
        score = 0.0
        score += 0.45 if garment.garment_type else 0.0
        score += 0.25 if has_descriptor else 0.0
        score += 0.2 if has_styling_context else 0.0
        score += 0.1 if garment.asset_id else 0.0
        missing_fields = garment.missing_attributes()
        clarification_focus = None
        if "garment_type" in missing_fields:
            clarification_focus = "garment_type"
        elif "color_or_material" in missing_fields:
            clarification_focus = "color_or_material"
        elif "styling_context" in missing_fields:
            clarification_focus = "styling_context"
        is_sufficient = bool(garment.garment_type and has_descriptor and has_styling_context)
        return GarmentCompletenessAssessment(
            missing_fields=missing_fields,
            clarification_focus=clarification_focus,
            completeness_score=min(score, 1.0),
            is_sufficient_for_generation=is_sufficient,
        )
