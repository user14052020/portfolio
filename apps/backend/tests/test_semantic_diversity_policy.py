import unittest

from app.domain.style_exploration.entities.style_direction import StyleDirection
from app.domain.style_exploration.policies.semantic_diversity_policy import SemanticDiversityPolicy


def make_style(
    style_id: str,
    *,
    palette: list[str],
    hero_garments: list[str],
    silhouette_family: str,
    materials: list[str],
    footwear: list[str],
    accessories: list[str],
) -> StyleDirection:
    return StyleDirection(
        style_id=style_id,
        style_name=style_id.replace("-", " ").title(),
        palette=palette,
        hero_garments=hero_garments,
        silhouette_family=silhouette_family,
        materials=materials,
        footwear=footwear,
        accessories=accessories,
    )


class SemanticDiversityPolicyTests(unittest.TestCase):
    def test_build_collects_semantic_anti_repeat_constraints_from_recent_history(self) -> None:
        policy = SemanticDiversityPolicy()
        history = [
            make_style(
                "artful-minimalism",
                palette=["chalk", "charcoal"],
                hero_garments=["structured coat"],
                silhouette_family="clean elongated",
                materials=["wool"],
                footwear=["derbies"],
                accessories=["watch"],
            ),
            make_style(
                "soft-retro-prep",
                palette=["camel", "cream"],
                hero_garments=["oxford shirt"],
                silhouette_family="relaxed collegiate",
                materials=["cotton"],
                footwear=["loafers"],
                accessories=["belt"],
            ),
        ]
        candidate = make_style(
            "gallery-noir",
            palette=["forest", "ink"],
            hero_garments=["field jacket"],
            silhouette_family="boxy layering",
            materials=["twill"],
            footwear=["boots"],
            accessories=["scarf"],
        )

        constraints = policy.build(history=history, candidate_style=candidate)

        self.assertEqual(
            constraints.avoid_palette,
            ["chalk", "charcoal", "camel", "cream"],
        )
        self.assertEqual(
            constraints.avoid_hero_garments,
            ["structured coat", "oxford shirt"],
        )
        self.assertEqual(
            constraints.avoid_silhouette_families,
            ["clean elongated", "relaxed collegiate"],
        )
        self.assertTrue(constraints.force_material_contrast)
        self.assertTrue(constraints.force_footwear_change)
        self.assertTrue(constraints.force_accessory_change)
        self.assertEqual(constraints.target_semantic_distance, "high")

    def test_build_with_empty_history_returns_medium_distance_without_constraints(self) -> None:
        policy = SemanticDiversityPolicy()
        candidate = make_style(
            "soft-retro-prep",
            palette=["camel", "cream"],
            hero_garments=["oxford shirt"],
            silhouette_family="relaxed collegiate",
            materials=["cotton"],
            footwear=["loafers"],
            accessories=["belt"],
        )

        constraints = policy.build(history=[], candidate_style=candidate)

        self.assertEqual(constraints.avoid_palette, [])
        self.assertEqual(constraints.avoid_hero_garments, [])
        self.assertEqual(constraints.target_semantic_distance, "medium")

