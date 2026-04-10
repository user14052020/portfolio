import unittest

from app.application.stylist_chat.handlers.garment_matching_handler import GarmentMatchingHandler
from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder


class GarmentMatchingHandlerLogicTests(unittest.TestCase):
    def build_handler(self) -> GarmentMatchingHandler:
        return GarmentMatchingHandler(
            clarification_builder=ClarificationMessageBuilder(),
            reasoner=object(),
            fallback_reasoner=object(),
            knowledge_provider=object(),
            reasoning_context_builder=object(),
            generation_request_builder=object(),
        )

    def test_extract_anchor_garment_marks_sufficient_text_description(self) -> None:
        handler = self.build_handler()

        anchor = handler.extract_anchor_garment(
            user_message="Dark indigo denim shirt with a straight fit",
            asset_name=None,
            profile_context={"gender": "male"},
        )

        self.assertEqual(anchor.garment_type, "shirt")
        self.assertEqual(anchor.material, "denim")
        self.assertEqual(anchor.fit, "straight")
        self.assertTrue(anchor.is_sufficient_for_generation)

    def test_extract_anchor_garment_uses_asset_name_when_message_is_empty(self) -> None:
        handler = self.build_handler()

        anchor = handler.extract_anchor_garment(
            user_message="",
            asset_name="black blazer reference.jpg",
            profile_context={},
        )

        self.assertEqual(anchor.raw_user_text, "black blazer reference.jpg")
        self.assertEqual(anchor.garment_type, "blazer")
        self.assertTrue(anchor.is_sufficient_for_generation)
