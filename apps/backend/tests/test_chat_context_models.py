import unittest

from app.domain.chat_context import AnchorGarment, OccasionContext


class ChatContextModelTests(unittest.TestCase):
    def test_anchor_garment_missing_attributes_reports_expected_slots(self) -> None:
        garment = AnchorGarment(raw_user_text="shirt")

        self.assertEqual(garment.missing_attributes(), ["garment_type", "anchor_attributes"])

    def test_occasion_context_missing_core_slots_reports_expected_fields(self) -> None:
        context = OccasionContext(event_type="wedding")

        self.assertEqual(
            context.missing_core_slots(),
            ["time_of_day", "season", "dress_code_or_desired_impression"],
        )

    def test_occasion_context_accepts_either_dress_code_or_desired_impression(self) -> None:
        with_dress_code = OccasionContext(
            event_type="wedding",
            time_of_day="evening",
            season="spring",
            dress_code="cocktail",
        )
        with_impression = OccasionContext(
            event_type="wedding",
            time_of_day="evening",
            season="spring",
            desired_impression="elegant",
        )

        self.assertEqual(with_dress_code.missing_core_slots(), [])
        self.assertEqual(with_impression.missing_core_slots(), [])
