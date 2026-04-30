import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeQuery(BaseModel):
    mode: str
    style_id: str | None = None
    style_ids: list[str | int] = Field(default_factory=list)
    style_name: str | None = None
    style_families: list[str] = Field(default_factory=list)
    eras: list[str] = Field(default_factory=list)
    anchor_garment: dict[str, Any] | None = None
    occasion_context: dict[str, Any] | None = None
    diversity_constraints: dict[str, Any] = Field(default_factory=dict)
    intent: str | None = None
    retrieval_profile: str | None = None
    need_visual_knowledge: bool = False
    need_historical_knowledge: bool = False
    need_styling_rules: bool = False
    need_color_poetics: bool = False
    limit: int = 10
    message: str | None = None
    user_request: str | None = None
    profile_context: dict[str, Any] = Field(default_factory=dict)

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]

    def resolved_style_ids(self) -> list[str]:
        result: list[str] = []
        if isinstance(self.style_id, str) and self.style_id.strip():
            result.append(self.style_id.strip())
        for value in self.style_ids:
            text = str(value).strip()
            if text and text not in result:
                result.append(text)
        return result

    def resolved_user_request(self) -> str | None:
        for value in (self.user_request, self.message):
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None
