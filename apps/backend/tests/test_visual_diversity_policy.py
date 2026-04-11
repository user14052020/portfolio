import unittest

from app.domain.style_exploration.entities.style_direction import StyleDirection
from app.domain.style_exploration.policies.visual_diversity_policy import VisualDiversityPolicy


def make_style(
    style_id: str,
    *,
    composition_type: str,
    background_family: str,
    layout_density: str,
    camera_distance: str,
    visual_preset: str,
) -> StyleDirection:
    return StyleDirection(
        style_id=style_id,
        style_name=style_id.replace("-", " ").title(),
        palette=[],
        hero_garments=[],
        footwear=[],
        accessories=[],
        materials=[],
        styling_mood=[],
        composition_type=composition_type,
        background_family=background_family,
        layout_density=layout_density,
        camera_distance=camera_distance,
        visual_preset=visual_preset,
    )


class VisualDiversityPolicyTests(unittest.TestCase):
    def test_build_rotates_visual_preset_and_collects_visual_constraints(self) -> None:
        policy = VisualDiversityPolicy()
        history = [
            make_style(
                "artful-minimalism",
                composition_type="editorial flat lay",
                background_family="stone",
                layout_density="compact",
                camera_distance="tight overhead",
                visual_preset="editorial_studio",
            ),
            make_style(
                "soft-retro-prep",
                composition_type="catalog grid",
                background_family="paper",
                layout_density="balanced",
                camera_distance="medium overhead",
                visual_preset="airy_catalog",
            ),
        ]

        constraints = policy.build(history=history, current_visual_presets=None)

        self.assertEqual(
            constraints.avoid_composition_types,
            ["editorial flat lay", "catalog grid"],
        )
        self.assertEqual(constraints.avoid_background_families, ["stone", "paper"])
        self.assertEqual(constraints.avoid_layout_density, ["compact", "balanced"])
        self.assertEqual(
            constraints.avoid_camera_distance,
            ["tight overhead", "medium overhead"],
        )
        self.assertTrue(constraints.force_visual_preset_shift)
        self.assertEqual(constraints.target_visual_distance, "high")
        self.assertEqual(constraints.suggested_visual_preset, "textured_surface")

    def test_build_with_empty_history_starts_from_default_rotation(self) -> None:
        policy = VisualDiversityPolicy()

        constraints = policy.build(history=[], current_visual_presets=None)

        self.assertEqual(constraints.avoid_composition_types, [])
        self.assertFalse(constraints.force_visual_preset_shift)
        self.assertEqual(constraints.target_visual_distance, "medium")
        self.assertEqual(constraints.suggested_visual_preset, "airy_catalog")

