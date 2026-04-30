import unittest

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.services.reasoning_context_builder import ReasoningContextBuilder
from app.domain.chat_context import ChatModeContext


class ReasoningContextBuilderTests(unittest.TestCase):
    def test_build_knowledge_query_carries_runtime_profile_context(self) -> None:
        builder = ReasoningContextBuilder()

        query = builder.build_knowledge_query(
            command=ChatCommand(
                session_id="session-1",
                locale="en",
                message="Show me another direction.",
                profile_context={
                    "presentation_profile": "androgynous",
                    "fit_preferences": ["relaxed"],
                    "height_cm": 176,
                    "weight_kg": 63,
                },
            ),
            context=ChatModeContext(current_style_name="Soft Tailoring"),
            mode="style_exploration",
        )

        self.assertEqual(query["profile_context"]["presentation_profile"], "androgynous")
        self.assertEqual(query["profile_context"]["fit_preferences"], ["relaxed"])
        self.assertEqual(query["body_height_cm"], 176)
        self.assertEqual(query["body_weight_kg"], 63)


if __name__ == "__main__":
    unittest.main()
