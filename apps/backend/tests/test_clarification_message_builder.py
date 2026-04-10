import unittest

from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment


class ClarificationMessageBuilderTests(unittest.TestCase):
    def test_garment_entry_prompt_is_direct_and_non_empty(self) -> None:
        builder = ClarificationMessageBuilder()

        prompt = builder.garment_entry_prompt("en")

        self.assertTrue(prompt)
        self.assertIn("garment", prompt.lower())

    def test_garment_clarification_prompt_for_missing_type_is_single_question(self) -> None:
        builder = ClarificationMessageBuilder()

        prompt = builder.garment_clarification_prompt("en", AnchorGarment(raw_user_text="something"))

        self.assertTrue(prompt.endswith(".") or prompt.endswith("?"))
        self.assertIn("garment", prompt.lower())
