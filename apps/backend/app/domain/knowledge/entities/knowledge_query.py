import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeQuery(BaseModel):
    mode: str
    style_id: str | None = None
    style_name: str | None = None
    anchor_garment: dict[str, Any] | None = None
    occasion_context: dict[str, Any] | None = None
    diversity_constraints: dict[str, Any] = Field(default_factory=dict)
    intent: str | None = None
    limit: int = 10
    message: str | None = None
    profile_context: dict[str, Any] = Field(default_factory=dict)

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
