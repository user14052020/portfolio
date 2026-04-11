import unittest

from app.application.stylist_chat.contracts.ports import OccasionExtractionOutput
from app.application.stylist_chat.services.occasion_extraction_service import OccasionExtractionService
from app.domain.chat_context import ChatModeContext
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext


class FakeOccasionExtractionReasoner:
    def __init__(self) -> None:
        self.output = OccasionExtractionOutput()

    async def extract_occasion_slots(
        self,
        *,
        locale: str,
        user_message: str,
        conversation_history: list[dict[str, str]],
        existing_slots: dict[str, str | None],
    ) -> OccasionExtractionOutput:
        return self.output


class OccasionExtractionServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_merges_llm_slots_and_detects_preferences(self) -> None:
        reasoner = FakeOccasionExtractionReasoner()
        reasoner.output = OccasionExtractionOutput(
            event_type="exhibition",
            venue="gallery",
            time_of_day="evening",
            season_or_weather="autumn",
            desired_impression="bold",
        )
        service = OccasionExtractionService(reasoner=reasoner)

        result = await service.extract(
            locale="en",
            user_message="Need something blue and comfortable, maybe a blazer, no heels",
            context=ChatModeContext(),
            existing_context=None,
            asset_metadata=None,
            fallback_history=[],
        )

        self.assertEqual(result.event_type, "exhibition")
        self.assertEqual(result.location, "gallery")
        self.assertEqual(result.time_of_day, "evening")
        self.assertEqual(result.season, "autumn")
        self.assertEqual(result.desired_impression, "bold")
        self.assertIn("blue", result.color_preferences)
        self.assertIn("blazer", result.garment_preferences)
        self.assertIn("comfort-first", result.comfort_requirements)
        self.assertIn("avoid heels", result.constraints)
        self.assertTrue(result.raw_user_texts)
        self.assertGreater(result.confidence, 0.0)

    async def test_extract_preserves_existing_slots_when_followup_only_adds_one_detail(self) -> None:
        reasoner = FakeOccasionExtractionReasoner()
        reasoner.output = OccasionExtractionOutput(time_of_day="evening")
        service = OccasionExtractionService(reasoner=reasoner)
        existing = OccasionContext(
            event_type="wedding",
            season="spring",
            desired_impression="elegant",
        )

        result = await service.extract(
            locale="en",
            user_message="In the evening",
            context=ChatModeContext(),
            existing_context=existing,
            asset_metadata=None,
            fallback_history=[],
        )

        self.assertEqual(result.event_type, "wedding")
        self.assertEqual(result.time_of_day, "evening")
        self.assertEqual(result.season, "spring")
        self.assertEqual(result.desired_impression, "elegant")

    async def test_extract_recognizes_exhibition_and_month_based_season_without_llm(self) -> None:
        service = OccasionExtractionService(reasoner=None)

        result = await service.extract(
            locale="en",
            user_message="An exhibition in October, in the evening",
            context=ChatModeContext(),
            existing_context=None,
            asset_metadata=None,
            fallback_history=[],
        )

        self.assertEqual(result.event_type, "exhibition")
        self.assertEqual(result.time_of_day, "evening")
        self.assertEqual(result.season, "autumn")
