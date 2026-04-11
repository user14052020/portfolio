from typing import Iterable

from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints
from app.domain.style_exploration.entities.style_direction import StyleDirection


class VisualDiversityPolicy:
    VISUAL_PRESET_ROTATION: tuple[str, ...] = (
        "airy_catalog",
        "editorial_studio",
        "textured_surface",
        "dark_gallery",
    )

    def build(
        self,
        *,
        history: list[StyleDirection],
        current_visual_presets: list[dict] | None = None,
    ) -> DiversityConstraints:
        recent = history[-2:]
        recent_visual_presets = self._unique(
            style.visual_preset for style in recent if style.visual_preset
        )
        suggested_visual_preset = next(
            (preset for preset in self.VISUAL_PRESET_ROTATION if preset not in recent_visual_presets),
            self.VISUAL_PRESET_ROTATION[0],
        )
        return DiversityConstraints(
            avoid_composition_types=self._unique(style.composition_type for style in recent if style.composition_type),
            avoid_background_families=self._unique(style.background_family for style in recent if style.background_family),
            avoid_layout_density=self._unique(style.layout_density for style in recent if style.layout_density),
            avoid_camera_distance=self._unique(style.camera_distance for style in recent if style.camera_distance),
            force_visual_preset_shift=bool(recent),
            target_visual_distance="high" if recent else "medium",
            suggested_visual_preset=suggested_visual_preset,
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
