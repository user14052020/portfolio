import unittest

from app.application.knowledge.use_cases.build_knowledge_query import BuildKnowledgeQueryUseCase
from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_context import ChatModeContext


class BuildKnowledgeQueryUseCaseTests(unittest.TestCase):
    def test_style_exploration_query_carries_style_and_diversity_context(self) -> None:
        query = BuildKnowledgeQueryUseCase().execute(
            command=ChatCommand(
                session_id="stage8-style-1",
                locale="en",
                message="Try another direction",
                profile_context={"gender": "female"},
            ),
            context=ChatModeContext(
                current_style_id="soft-retro-prep",
                current_style_name="Soft Retro Prep",
            ),
            mode="style_exploration",
            intent="style_exploration",
            style_id="soft-retro-prep",
            style_name="Soft Retro Prep",
            diversity_constraints={"avoid_palette": ["camel", "cream"]},
            limit=8,
        )

        self.assertEqual(query.mode, "style_exploration")
        self.assertEqual(query.style_id, "soft-retro-prep")
        self.assertEqual(query.style_name, "Soft Retro Prep")
        self.assertEqual(query.diversity_constraints["avoid_palette"], ["camel", "cream"])
        self.assertEqual(query.profile_context["gender"], "female")
        self.assertEqual(query.limit, 8)

    def test_garment_query_uses_anchor_garment_and_message(self) -> None:
        query = BuildKnowledgeQueryUseCase().execute(
            command=ChatCommand(
                session_id="stage8-garment-1",
                locale="en",
                message="Style around my black leather jacket",
            ),
            context=ChatModeContext(),
            mode="garment_matching",
            intent="anchor_garment",
            anchor_garment={
                "garment_type": "jacket",
                "material": "leather",
                "color_primary": "black",
            },
            limit=5,
        )

        self.assertEqual(query.mode, "garment_matching")
        self.assertEqual(query.anchor_garment["garment_type"], "jacket")
        self.assertEqual(query.anchor_garment["material"], "leather")
        self.assertEqual(query.message, "Style around my black leather jacket")
        self.assertEqual(query.limit, 5)
