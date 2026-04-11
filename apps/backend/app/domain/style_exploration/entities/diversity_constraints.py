import hashlib
import json

from pydantic import BaseModel, Field


class DiversityConstraints(BaseModel):
    avoid_palette: list[str] = Field(default_factory=list)
    avoid_hero_garments: list[str] = Field(default_factory=list)
    avoid_silhouette_families: list[str] = Field(default_factory=list)
    avoid_materials: list[str] = Field(default_factory=list)
    avoid_footwear: list[str] = Field(default_factory=list)
    avoid_accessories: list[str] = Field(default_factory=list)
    avoid_composition_types: list[str] = Field(default_factory=list)
    avoid_background_families: list[str] = Field(default_factory=list)
    avoid_layout_density: list[str] = Field(default_factory=list)
    avoid_camera_distance: list[str] = Field(default_factory=list)
    force_material_contrast: bool = False
    force_footwear_change: bool = False
    force_accessory_change: bool = False
    force_visual_preset_shift: bool = False
    target_semantic_distance: str | None = None
    target_visual_distance: str | None = None
    suggested_visual_preset: str | None = None

    def semantic_payload(self) -> dict[str, object]:
        return {
            "avoid_palette": self.avoid_palette,
            "avoid_hero_garments": self.avoid_hero_garments,
            "avoid_silhouette_families": self.avoid_silhouette_families,
            "avoid_materials": self.avoid_materials,
            "avoid_footwear": self.avoid_footwear,
            "avoid_accessories": self.avoid_accessories,
            "force_material_contrast": self.force_material_contrast,
            "force_footwear_change": self.force_footwear_change,
            "force_accessory_change": self.force_accessory_change,
            "target_semantic_distance": self.target_semantic_distance,
        }

    def visual_payload(self) -> dict[str, object]:
        return {
            "avoid_composition_types": self.avoid_composition_types,
            "avoid_background_families": self.avoid_background_families,
            "avoid_layout_density": self.avoid_layout_density,
            "avoid_camera_distance": self.avoid_camera_distance,
            "force_visual_preset_shift": self.force_visual_preset_shift,
            "target_visual_distance": self.target_visual_distance,
            "suggested_visual_preset": self.suggested_visual_preset,
        }

    def semantic_hash(self) -> str:
        payload = json.dumps(self.semantic_payload(), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]

    def visual_hash(self) -> str:
        payload = json.dumps(self.visual_payload(), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]

    def to_reasoning_dict(self) -> dict[str, object]:
        return {
            **self.semantic_payload(),
            **self.visual_payload(),
            "semantic_constraints_hash": self.semantic_hash(),
            "visual_constraints_hash": self.visual_hash(),
        }
