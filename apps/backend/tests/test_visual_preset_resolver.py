import unittest

from app.application.visual_generation.services.visual_preset_resolver import VisualPresetResolver
from app.domain.prompt_building.entities.fashion_brief import FashionBrief


class VisualPresetResolverTests(unittest.IsolatedAsyncioTestCase):
    async def test_garment_matching_forces_anchor_centric_visual_priority(self) -> None:
        preset = await VisualPresetResolver().resolve(
            mode="garment_matching",
            fashion_brief=FashionBrief(
                style_identity="Black Leather Jacket",
                brief_mode="garment_matching",
                garment_list=["leather jacket", "black trousers"],
                palette=["black"],
                materials=["leather"],
                visual_preset="textured_surface",
            ),
        )

        self.assertEqual(preset.anchor_garment_centrality, "high")
        self.assertEqual(preset.layout_archetype, "centered anchor composition")
        self.assertEqual(preset.object_count_range, "balanced outfit set")

    async def test_style_exploration_avoids_recent_visual_collision(self) -> None:
        preset = await VisualPresetResolver().resolve(
            mode="style_exploration",
            fashion_brief=FashionBrief(
                style_identity="Soft Retro Prep",
                brief_mode="style_exploration",
                palette=["camel", "cream"],
                garment_list=["oxford shirt"],
                materials=["cotton"],
                diversity_constraints={
                    "force_visual_preset_shift": True,
                    "avoid_background_families": ["warm wood"],
                    "avoid_camera_distance": ["wider editorial overhead"],
                },
            ),
            style_history=[{"visual_preset": "editorial_studio"}],
        )

        self.assertNotEqual(preset.id, "editorial_studio")
        self.assertNotEqual((preset.background_family or "").lower(), "warm wood")
        self.assertNotEqual((preset.camera_distance or "").lower(), "wider editorial overhead")
        self.assertEqual(preset.diversity_bias, "high")

    async def test_occasion_outfit_prioritizes_practical_coherence(self) -> None:
        preset = await VisualPresetResolver().resolve(
            mode="occasion_outfit",
            fashion_brief=FashionBrief(
                style_identity="Exhibition Outfit",
                brief_mode="occasion_outfit",
                occasion_context={"event_type": "exhibition", "dress_code": "smart casual"},
                palette=["olive"],
                garment_list=["relaxed blazer"],
                materials=["cotton twill"],
            ),
        )

        self.assertEqual(preset.practical_coherence, "high")
        self.assertEqual(preset.layout_archetype, "practical dressing board")
        self.assertEqual(preset.spacing_density, "balanced")
