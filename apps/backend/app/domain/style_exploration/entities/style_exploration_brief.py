from pydantic import BaseModel, Field

from .diversity_constraints import DiversityConstraints
from .style_direction import StyleDirection


class StyleExplorationBrief(BaseModel):
    style_identity: str
    style_family: str | None = None
    style_summary: str
    historical_reference: list[str] = Field(default_factory=list)
    tailoring_logic: list[str] = Field(default_factory=list)
    color_logic: list[str] = Field(default_factory=list)
    garment_list: list[str] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    footwear: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    styling_notes: list[str] = Field(default_factory=list)
    composition_rules: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    diversity_constraints: DiversityConstraints
    selected_style_direction: StyleDirection
    visual_preset: str | None = None
    composition_type: str | None = None
    background_family: str | None = None
    semantic_constraints_hash: str | None = None
    visual_constraints_hash: str | None = None
    diversity_constraints_hash: str | None = None

    def to_prompt_payload(self) -> dict[str, object]:
        return {
            "brief_type": "style_exploration",
            "style_identity": self.style_identity,
            "style_family": self.style_family,
            "style_summary": self.style_summary,
            "historical_reference": self.historical_reference,
            "tailoring_logic": self.tailoring_logic,
            "color_logic": self.color_logic,
            "garment_list": self.garment_list,
            "palette": self.palette,
            "materials": self.materials,
            "footwear": self.footwear,
            "accessories": self.accessories,
            "styling_notes": self.styling_notes,
            "composition_rules": self.composition_rules,
            "negative_constraints": self.negative_constraints,
            "diversity_constraints": self.diversity_constraints.model_dump(mode="json"),
            "selected_style_direction": self.selected_style_direction.model_dump(mode="json"),
            "visual_preset": self.visual_preset,
            "composition_type": self.composition_type,
            "background_family": self.background_family,
            "semantic_constraints_hash": self.semantic_constraints_hash,
            "visual_constraints_hash": self.visual_constraints_hash,
            "diversity_constraints_hash": self.diversity_constraints_hash,
        }
