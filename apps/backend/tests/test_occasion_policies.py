import unittest

from app.domain.chat_modes import ClarificationKind
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext
from app.domain.occasion_outfit.policies.occasion_clarification_policy import OccasionClarificationPolicy
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessPolicy


class OccasionPoliciesTests(unittest.TestCase):
    def test_completeness_policy_marks_minimal_ready_context_as_sufficient(self) -> None:
        assessment = OccasionCompletenessPolicy().evaluate(
            OccasionContext(
                event_type="wedding",
                time_of_day="day",
                season="summer",
                desired_impression="elegant",
            )
        )

        self.assertTrue(assessment.is_sufficient_for_generation)
        self.assertEqual(assessment.missing_slots, [])
        self.assertGreater(assessment.completeness_score, 0.8)

    def test_clarification_policy_selects_next_missing_core_slot(self) -> None:
        context = OccasionContext(event_type="exhibition")
        assessment = OccasionCompletenessPolicy().evaluate(context)

        kind, text = OccasionClarificationPolicy().build(
            locale="en",
            context=context,
            assessment=assessment,
        )

        self.assertEqual(kind, ClarificationKind.OCCASION_TIME_OF_DAY)
        self.assertIn("time of day", text.lower())

    def test_clarification_policy_asks_for_style_signal_when_only_that_pair_is_missing(self) -> None:
        context = OccasionContext(
            event_type="wedding",
            time_of_day="evening",
            season="spring",
        )
        assessment = OccasionCompletenessPolicy().evaluate(context)

        kind, text = OccasionClarificationPolicy().build(
            locale="en",
            context=context,
            assessment=assessment,
        )

        self.assertEqual(kind, ClarificationKind.OCCASION_DRESS_CODE)
        self.assertIn("dress code", text.lower())
