import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field


class CompiledImagePrompt(BaseModel):
    final_prompt: str
    negative_prompt: str
    visual_preset: str | None = None
    palette_tags: list[str] = Field(default_factory=list)
    garment_tags: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    composition_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
