import unittest

from app.application.stylist_chat.services.diversity_constraints_builder import DiversityConstraintsBuilder
from app.domain.chat_context import StyleDirectionContext


class DiversityConstraintsBuilderTests(unittest.TestCase):
    def test_build_collects_unique_anti_repeat_constraints(self) -> None:
        builder = DiversityConstraintsBuilder()
        history = [
            StyleDirectionContext(
                style_id="style-a",
                style_name="Style A",
                palette=["navy", "white"],
                silhouette="clean",
                hero_garments=["blazer", "loafer"],
                composition_type="flat lay",
            ),
            StyleDirectionContext(
                style_id="style-b",
                style_name="Style B",
                palette=["white", "olive"],
                silhouette="relaxed",
                hero_garments=["overshirt", "loafer"],
                composition_type="studio",
            ),
        ]

        constraints = builder.build(history)

        self.assertEqual(constraints["avoid_previous_palette"], ["navy", "white", "olive"])
        self.assertEqual(constraints["avoid_previous_silhouette"], ["clean", "relaxed"])
        self.assertEqual(constraints["avoid_previous_hero_garments"], ["blazer", "loafer", "overshirt"])
        self.assertEqual(constraints["avoid_previous_composition"], ["flat lay", "studio"])
