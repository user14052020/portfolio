import unittest

from app.application.stylist_chat.services.style_history_service import StyleHistoryService
from app.domain.chat_context import StyleDirectionContext


def make_style(
    style_id: str,
    *,
    style_name: str | None = None,
    palette: list[str] | None = None,
    hero_garments: list[str] | None = None,
    silhouette_family: str | None = None,
    visual_preset: str | None = None,
) -> StyleDirectionContext:
    return StyleDirectionContext(
        style_id=style_id,
        style_name=style_name or style_id.replace("-", " ").title(),
        palette=palette or [],
        hero_garments=hero_garments or [],
        silhouette_family=silhouette_family,
        footwear=[],
        accessories=[],
        materials=[],
        styling_mood=[],
        visual_preset=visual_preset,
    )


class StyleHistoryServiceTests(unittest.TestCase):
    def test_merge_preserves_recent_unique_style_directions(self) -> None:
        service = StyleHistoryService()
        persisted_history = [
            make_style("artful-minimalism", visual_preset="editorial_studio"),
            make_style("soft-retro-prep", visual_preset="airy_catalog"),
        ]
        context_history = [
            make_style("soft-retro-prep", visual_preset="textured_surface"),
            make_style("gallery-noir", visual_preset="dark_gallery"),
        ]

        merged = service.merge(
            context_history=context_history,
            persisted_history=persisted_history,
        )

        self.assertEqual(
            [item.style_id for item in merged],
            ["artful-minimalism", "soft-retro-prep", "gallery-noir"],
        )
        self.assertEqual(merged[1].visual_preset, "textured_surface")

    def test_remember_caps_history_and_moves_duplicate_to_the_end(self) -> None:
        service = StyleHistoryService()
        history = [
            make_style("style-1"),
            make_style("style-2"),
            make_style("style-3"),
            make_style("style-4"),
            make_style("style-5"),
        ]

        updated = service.remember(
            history=history,
            style_direction=make_style("style-3", visual_preset="textured_surface"),
        )
        rotated = service.remember(
            history=updated,
            style_direction=make_style("style-6"),
        )

        self.assertEqual(
            [item.style_id for item in updated],
            ["style-1", "style-2", "style-4", "style-5", "style-3"],
        )
        self.assertEqual(updated[-1].visual_preset, "textured_surface")
        self.assertEqual(
            [item.style_id for item in rotated],
            ["style-2", "style-4", "style-5", "style-3", "style-6"],
        )

