from typing import Any

from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.visual_generation import VisualPreset
from app.infrastructure.comfy.presets.visual_presets_registry import (
    get_visual_preset,
    list_visual_presets,
)


class VisualPresetResolver:
    async def resolve(
        self,
        mode: str,
        fashion_brief: FashionBrief,
        style_history: list[dict[str, Any]] | None = None,
        diversity_constraints: dict[str, Any] | None = None,
    ) -> VisualPreset:
        history = list(style_history or [])
        constraints = dict(diversity_constraints or fashion_brief.diversity_constraints or {})
        recent_presets = {
            str(item.get("visual_preset")).strip()
            for item in history[-4:]
            if isinstance(item, dict) and str(item.get("visual_preset") or "").strip()
        }
        requested_preset = (fashion_brief.visual_preset or "").strip()
        if requested_preset:
            preset = get_visual_preset(requested_preset)
            if preset is not None and self._preset_allowed(preset=preset, recent_presets=recent_presets, mode=mode, constraints=constraints):
                return self._apply_overrides(preset=preset, mode=mode, fashion_brief=fashion_brief, constraints=constraints)

        candidates = [
            preset
            for preset in list_visual_presets()
            if mode in preset.mode_affinity or not preset.mode_affinity
        ]
        for preset in candidates:
            if self._preset_allowed(preset=preset, recent_presets=recent_presets, mode=mode, constraints=constraints):
                return self._apply_overrides(preset=preset, mode=mode, fashion_brief=fashion_brief, constraints=constraints)

        fallback = get_visual_preset("editorial_studio")
        if fallback is None:
            raise RuntimeError("editorial_studio preset is not configured")
        return self._apply_overrides(preset=fallback, mode=mode, fashion_brief=fashion_brief, constraints=constraints)

    def _preset_allowed(
        self,
        *,
        preset: VisualPreset,
        recent_presets: set[str],
        mode: str,
        constraints: dict[str, Any],
    ) -> bool:
        if mode == "style_exploration" and preset.id in recent_presets:
            return False
        if constraints.get("force_visual_preset_shift") and preset.id in recent_presets:
            return False
        return True

    def _apply_overrides(
        self,
        *,
        preset: VisualPreset,
        mode: str,
        fashion_brief: FashionBrief,
        constraints: dict[str, Any],
    ) -> VisualPreset:
        updated = preset.model_copy(deep=True)
        if mode == "garment_matching":
            updated.anchor_garment_centrality = "high"
            updated.practical_coherence = updated.practical_coherence or "medium"
            updated.layout_archetype = "centered anchor composition"
            updated.object_count_range = "balanced outfit set"
            updated.spacing_density = "balanced"
        elif mode == "occasion_outfit":
            updated.practical_coherence = "high"
            updated.anchor_garment_centrality = updated.anchor_garment_centrality or "medium"
            updated.layout_archetype = "practical dressing board"
            updated.object_count_range = "balanced outfit set"
            updated.spacing_density = "balanced"
        elif mode == "style_exploration":
            updated.diversity_bias = "high"

        avoid_backgrounds = {str(item).strip().lower() for item in constraints.get("avoid_background_families", []) if str(item).strip()}
        if updated.background_family and updated.background_family.lower() in avoid_backgrounds:
            updated.background_family = self._fallback_background(mode=mode, brief=fashion_brief)

        avoid_camera = {str(item).strip().lower() for item in constraints.get("avoid_camera_distance", []) if str(item).strip()}
        if updated.camera_distance and updated.camera_distance.lower() in avoid_camera:
            updated.camera_distance = "wider editorial overhead" if updated.camera_distance != "wider editorial overhead" else "medium flat lay"

        avoid_layouts = {str(item).strip().lower() for item in constraints.get("avoid_composition_types", []) if str(item).strip()}
        if updated.layout_archetype and updated.layout_archetype.lower() in avoid_layouts:
            updated.layout_archetype = self._fallback_layout(mode=mode)
        return updated

    def _fallback_background(self, *, mode: str, brief: FashionBrief) -> str:
        palette = {str(item).strip().lower() for item in brief.palette if str(item).strip()}
        if mode == "garment_matching" and "black" in palette:
            return "cool stone"
        if mode == "occasion_outfit":
            return "muted studio background"
        if "camel" in palette or "cream" in palette:
            return "off-white linen"
        return "neutral paper"

    def _fallback_layout(self, *, mode: str) -> str:
        if mode == "garment_matching":
            return "centered anchor composition"
        if mode == "occasion_outfit":
            return "practical dressing board"
        return "diagonal editorial spread"
