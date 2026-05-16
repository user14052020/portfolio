import unittest
from types import SimpleNamespace

from app.application.stylist_chat.services.random_style_response_composer import (
    RandomStyleResponseComposer,
)
from app.domain.style_exploration.entities.style_direction import StyleDirection


class RandomStyleResponseComposerTests(unittest.TestCase):
    def test_ru_response_includes_several_history_sentences(self) -> None:
        composer = RandomStyleResponseComposer()
        source_model = SimpleNamespace(
            metadata={
                "core_definition": "A late-1950s London youth style centered on sharp tailoring, scooters, slim suits, polos, miniskirts, RAF roundels, modern jazz, soul, clean grooming, and precise modernist presentation.",
                "historical_notes": [
                    "The source defines Mod through London modernists, scooters, tailored clothing, jazz, soul, R&B taste, and sharp youth presentation.",
                    "The style grew from youth clubs, music taste, and clean modernist presentation rather than from generic 1960s costume.",
                ],
                "era": ["late 1950s", "1960s"],
                "origin_regions": ["London", "England"],
                "platforms": ["music clubs", "scooter culture", "British youth fashion"],
                "related_styles": ["Britpop", "Mod Revival", "Ivy"],
                "palette": ["black", "white", "red", "navy"],
                "hero_garments": ["slim suit", "button-down shirt", "polo shirt"],
                "shoes": ["loafers"],
                "core_accessories": ["RAF roundel pin", "skinny tie"],
                "materials": ["wool", "cotton"],
                "what_makes_it_distinct": ["sharp tailoring and scooter-culture precision"],
            }
        )

        text = composer.compose(
            locale="ru",
            style_direction=StyleDirection(
                style_id="mod",
                style_name="Mod",
                palette=["black", "white", "red"],
                silhouette_family="sharp slim tailoring",
                hero_garments=["slim suit", "button-down shirt"],
                footwear=["loafers"],
                accessories=["RAF roundel pin"],
                materials=["wool", "cotton"],
                styling_mood=["precise", "modernist"],
                composition_type="editorial flat lay",
                background_family="studio",
            ),
            source_model=source_model,
        )

        history_markers = (
            "Исторически",
            "Источник фиксирует",
            "По происхождению",
            "Культурные маркеры",
            "По соседним",
        )
        history_sentence_count = sum(text.count(marker) for marker in history_markers)

        self.assertTrue(text.startswith("Случайный стиль: Mod."))
        self.assertGreaterEqual(history_sentence_count, 3)
        self.assertNotIn("В базе", text)
        self.assertNotIn("читается как отдельное стилевое направление", text)
        self.assertIn("Ключевые вещи", text)
        self.assertIn("Палитра", text)


if __name__ == "__main__":
    unittest.main()
