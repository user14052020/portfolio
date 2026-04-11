import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field


class FashionBrief(BaseModel):
    style_identity: str
    style_family: str | None = None
    brief_mode: str
    occasion_context: dict[str, Any] | None = None
    anchor_garment: dict[str, Any] | None = None
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
    diversity_constraints: dict[str, Any] = Field(default_factory=dict)
    visual_preset: str | None = None
    generation_intent: str | None = None
    knowledge_cards: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
