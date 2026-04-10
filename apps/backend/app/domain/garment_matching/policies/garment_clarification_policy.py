from app.domain.chat_modes import ClarificationKind
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment
from app.domain.garment_matching.policies.garment_completeness_policy import GarmentCompletenessAssessment


class GarmentClarificationPolicy:
    def build(
        self,
        *,
        locale: str,
        garment: AnchorGarment,
        assessment: GarmentCompletenessAssessment,
    ) -> tuple[ClarificationKind, str]:
        if assessment.clarification_focus == "garment_type":
            text = (
                "Уточните, пожалуйста, что это за вещь: рубашка, жакет, куртка, платье или что-то другое?"
                if locale == "ru"
                else "What kind of garment is it: a shirt, blazer, jacket, dress, or something else?"
            )
            return ClarificationKind.ANCHOR_GARMENT_MISSING_ATTRIBUTES, text
        if assessment.clarification_focus == "color_or_material":
            noun = garment.garment_type or ("вещь" if locale == "ru" else "garment")
            text = (
                f"Какого цвета {noun} или из какого она материала?"
                if locale == "ru"
                else f"What color is the {noun}, or what material is it made from?"
            )
            return ClarificationKind.ANCHOR_GARMENT_MISSING_ATTRIBUTES, text
        text = (
            "Это более повседневная, сезонная или нарядная вещь?"
            if locale == "ru"
            else "Is it more casual, seasonal, or dressy?"
        )
        return ClarificationKind.ANCHOR_GARMENT_MISSING_ATTRIBUTES, text
