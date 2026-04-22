import unittest

from pydantic import ValidationError

from app.ingestion.styles.style_chatgpt_payloads import StyleEnrichmentPayload


def _minimal_payload() -> dict[str, object]:
    return {
        "knowledge": {},
        "visual_language": {},
        "fashion_items": {},
        "image_prompt_atoms": {},
        "relations": {},
        "presentation": {},
    }


class StyleEnrichmentPayloadTests(unittest.TestCase):
    def test_payload_rejects_unknown_top_level_fields(self) -> None:
        payload = {
            **_minimal_payload(),
            "unexpected_block": {},
        }

        with self.assertRaises(ValidationError):
            StyleEnrichmentPayload.model_validate(payload)

    def test_payload_requires_all_typed_blocks(self) -> None:
        payload = _minimal_payload()
        payload.pop("image_prompt_atoms")

        with self.assertRaises(ValidationError):
            StyleEnrichmentPayload.model_validate(payload)

    def test_payload_normalizes_text_and_deduplicates_lists(self) -> None:
        payload = {
            **_minimal_payload(),
            "knowledge": {
                "style_name": "  Soft   Academia  ",
                "core_definition": "  Bookish    softness  ",
                "core_style_logic": [" layered neutrals ", "Layered Neutrals", "", None],
                "styling_rules": " structured knitwear ",
            },
            "visual_language": {
                "palette": [" cream ", "Cream", "warm brown"],
                "lighting_mood": " soft daylight ",
            },
            "presentation": {
                "short_explanation": "  Quiet   study-room romance. ",
                "what_makes_it_distinct": ["books", " Books ", "warmth"],
            },
        }

        parsed = StyleEnrichmentPayload.model_validate(payload)

        self.assertEqual(parsed.knowledge.style_name, "Soft Academia")
        self.assertEqual(parsed.knowledge.core_definition, "Bookish softness")
        self.assertEqual(parsed.knowledge.core_style_logic, ["layered neutrals"])
        self.assertEqual(parsed.knowledge.styling_rules, ["structured knitwear"])
        self.assertEqual(parsed.visual_language.palette, ["cream", "warm brown"])
        self.assertEqual(parsed.visual_language.lighting_mood, ["soft daylight"])
        self.assertEqual(parsed.presentation.short_explanation, "Quiet study-room romance.")
        self.assertEqual(parsed.presentation.what_makes_it_distinct, ["books", "warmth"])


if __name__ == "__main__":
    unittest.main()
