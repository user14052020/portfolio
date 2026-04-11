import unittest

from app.application.stylist_chat.contracts.ports import KnowledgeItem, KnowledgeResult
from app.application.stylist_chat.services.occasion_brief_compiler import OccasionBriefCompiler
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext


class OccasionBriefCompilerTests(unittest.IsolatedAsyncioTestCase):
    async def test_compile_exposes_recommended_stage_five_fields(self) -> None:
        compiler = OccasionBriefCompiler()
        brief = await compiler.build(
            occasion_context=OccasionContext(
                event_type="exhibition",
                time_of_day="evening",
                season="autumn",
                desired_impression="bold",
            ),
            context={"profile_context": {"gender": "female"}},
            knowledge_result=KnowledgeResult(
                items=[
                    KnowledgeItem("dress_code", "Respect the event formality first."),
                    KnowledgeItem("silhouette", "Keep one polished silhouette line."),
                ],
                source="test",
            ),
        )

        compiled = compiler.compile(brief)

        self.assertEqual(compiled["brief_type"], "occasion_outfit")
        self.assertIn("dress_code_logic", compiled)
        self.assertIn("impression_logic", compiled)
        self.assertIn("color_logic", compiled)
        self.assertIn("silhouette_logic", compiled)
        self.assertIn("garment_recommendations", compiled)
        self.assertIn("footwear_recommendations", compiled)
        self.assertIn("accessories", compiled)
        self.assertIn("outerwear_notes", compiled)
        self.assertIn("comfort_notes", compiled)
        self.assertIn("historical_reference", compiled)
        self.assertIn("tailoring_notes", compiled)
        self.assertIn("negative_constraints", compiled)
        self.assertIn("image_prompt_notes", compiled)
