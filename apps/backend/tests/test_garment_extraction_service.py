import unittest

from app.application.stylist_chat.services.garment_extraction_service import RuleBasedGarmentExtractor
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment


class GarmentExtractionServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_extracts_sufficient_anchor_from_text(self) -> None:
        extractor = RuleBasedGarmentExtractor()

        anchor = await extractor.extract("Dark indigo denim shirt with an oversized fit")

        self.assertEqual(anchor.garment_type, "shirt")
        self.assertEqual(anchor.color_primary, "navy")
        self.assertEqual(anchor.material, "denim")
        self.assertEqual(anchor.fit, "oversized")
        self.assertIn("casual", anchor.style_hints)

    async def test_merges_followup_with_existing_anchor(self) -> None:
        extractor = RuleBasedGarmentExtractor()
        existing = AnchorGarment(raw_user_text="shirt", garment_type="shirt")

        anchor = await extractor.extract("white linen", existing_anchor=existing)

        self.assertEqual(anchor.garment_type, "shirt")
        self.assertEqual(anchor.color_primary, "white")
        self.assertEqual(anchor.material, "linen")
        self.assertIn("shirt", anchor.raw_user_text)

    async def test_asset_id_increases_confidence_without_becoming_gatekeeper(self) -> None:
        extractor = RuleBasedGarmentExtractor()

        anchor = await extractor.extract("", asset_id="asset-77")

        self.assertEqual(anchor.asset_id, "asset-77")
        self.assertGreater(anchor.confidence, 0.2)
        self.assertIsNone(anchor.garment_type)
