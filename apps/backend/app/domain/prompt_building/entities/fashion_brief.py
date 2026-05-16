import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field, model_validator


class FashionBrief(BaseModel):
    intent: str = ""
    style_direction: str | None = None
    style_identity: str = ""
    style_family: str | None = None
    brief_mode: str = ""
    occasion_context: dict[str, Any] | None = None
    anchor_garment: dict[str, Any] | None = None
    historical_reference: list[str] = Field(default_factory=list)
    tailoring_logic: list[str] = Field(default_factory=list)
    color_logic: list[str] = Field(default_factory=list)
    silhouette: str | None = None
    hero_garments: list[str] = Field(default_factory=list)
    secondary_garments: list[str] = Field(default_factory=list)
    garment_list: list[str] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    footwear: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    visual_motifs: list[str] = Field(default_factory=list)
    lighting_mood: list[str] = Field(default_factory=list)
    styling_notes: list[str] = Field(default_factory=list)
    composition_rules: list[str] = Field(default_factory=list)
    photo_treatment: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    diversity_constraints: dict[str, Any] = Field(default_factory=dict)
    visual_preset: str | None = None
    generation_intent: str | None = None
    knowledge_cards: list[dict[str, Any]] = Field(default_factory=list)
    source_style_facet_ids: list[str] = Field(default_factory=list)
    brief_confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def fill_compatibility_fields(self) -> "FashionBrief":
        if not self.intent:
            self.intent = self.brief_mode or self.generation_intent or "fashion_brief"
        if self.style_direction is None and self.style_identity:
            self.style_direction = self.style_identity
        if not self.style_identity and self.style_direction:
            self.style_identity = self.style_direction
        if not self.brief_mode:
            self.brief_mode = self.intent
        return self

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
