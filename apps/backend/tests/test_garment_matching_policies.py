import unittest

from app.domain.chat_modes import ClarificationKind
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment
from app.domain.garment_matching.policies.garment_clarification_policy import GarmentClarificationPolicy
from app.domain.garment_matching.policies.garment_completeness_policy import GarmentCompletenessPolicy


class GarmentMatchingPolicyTests(unittest.TestCase):
    def test_completeness_policy_marks_black_leather_jacket_as_sufficient(self) -> None:
        policy = GarmentCompletenessPolicy()

        assessment = policy.evaluate(
            AnchorGarment(
                raw_user_text="black leather jacket",
                garment_type="jacket",
                color_primary="black",
                material="leather",
                style_hints=["edgy"],
            )
        )

        self.assertTrue(assessment.is_sufficient_for_generation)
        self.assertGreaterEqual(assessment.completeness_score, 0.7)

    def test_completeness_policy_marks_single_word_shirt_as_incomplete(self) -> None:
        policy = GarmentCompletenessPolicy()

        assessment = policy.evaluate(AnchorGarment(raw_user_text="shirt", garment_type="shirt"))

        self.assertFalse(assessment.is_sufficient_for_generation)
        self.assertIn("color_or_material", assessment.missing_fields)
        self.assertEqual(assessment.clarification_focus, "color_or_material")

    def test_clarification_policy_returns_one_short_question(self) -> None:
        completeness_policy = GarmentCompletenessPolicy()
        clarification_policy = GarmentClarificationPolicy()
        garment = AnchorGarment(raw_user_text="shirt", garment_type="shirt")
        assessment = completeness_policy.evaluate(garment)

        kind, text = clarification_policy.build(locale="en", garment=garment, assessment=assessment)

        self.assertEqual(kind, ClarificationKind.ANCHOR_GARMENT_MISSING_ATTRIBUTES)
        self.assertEqual(text.count("?"), 1)
