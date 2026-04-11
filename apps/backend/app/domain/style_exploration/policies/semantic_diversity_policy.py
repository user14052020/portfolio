from typing import Iterable

from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints
from app.domain.style_exploration.entities.style_direction import StyleDirection


class SemanticDiversityPolicy:
    def build(
        self,
        *,
        history: list[StyleDirection],
        candidate_style: StyleDirection,
        session_context: dict | None = None,
    ) -> DiversityConstraints:
        recent = history[-2:]
        candidate_key = candidate_style.key()
        semantic_distance = "high" if recent else "medium"
        return DiversityConstraints(
            avoid_palette=self._unique(color for style in recent for color in style.palette),
            avoid_hero_garments=self._unique(
                garment for style in recent for garment in style.hero_garments if garment not in candidate_style.hero_garments
            ),
            avoid_silhouette_families=self._unique(
                style.silhouette_family for style in recent if style.silhouette_family and style.silhouette_family != candidate_style.silhouette_family
            ),
            avoid_materials=self._unique(
                material for style in recent for material in style.materials if material not in candidate_style.materials
            ),
            avoid_footwear=self._unique(
                item for style in recent for item in style.footwear if item not in candidate_style.footwear
            ),
            avoid_accessories=self._unique(
                item for style in recent for item in style.accessories if item not in candidate_style.accessories
            ),
            force_material_contrast=bool(recent),
            force_footwear_change=bool(recent),
            force_accessory_change=bool(recent),
            target_semantic_distance=semantic_distance if candidate_key else "medium",
        )

    def _unique(self, values: Iterable[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = value.strip() if isinstance(value, str) else ""
            lowered = cleaned.lower()
            if not cleaned or lowered in seen:
                continue
            seen.add(lowered)
            result.append(cleaned)
        return result
