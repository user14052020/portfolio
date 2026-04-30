import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field


class VisualGenerationPlan(BaseModel):
    mode: str
    style_id: str | None = None
    style_name: str | None = None
    fashion_brief_hash: str | None = None
    compiled_prompt_hash: str | None = None
    final_prompt: str
    negative_prompt: str
    visual_preset_id: str | None = None
    workflow_name: str
    workflow_version: str | None = None
    layout_archetype: str | None = None
    background_family: str | None = None
    object_count_range: str | None = None
    spacing_density: str | None = None
    camera_distance: str | None = None
    shadow_hardness: str | None = None
    anchor_garment_centrality: str | None = None
    practical_coherence: str | None = None
    diversity_profile: dict[str, Any] = Field(default_factory=dict)
    profile_constraints: dict[str, Any] = Field(default_factory=dict)
    profile_context_snapshot: dict[str, Any] | None = None
    palette_tags: list[str] = Field(default_factory=list)
    garments_tags: list[str] = Field(default_factory=list)
    materials_tags: list[str] = Field(default_factory=list)
    knowledge_refs: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
