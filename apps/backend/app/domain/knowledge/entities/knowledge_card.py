import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from app.domain.knowledge.enums.knowledge_type import KnowledgeType


class KnowledgeCard(BaseModel):
    id: str
    knowledge_type: KnowledgeType
    provider_code: str | None = None
    provider_priority: int | None = None
    title: str
    summary: str
    body: str | None = None
    tone_role: str | None = None
    tags: list[str] = Field(default_factory=list)
    style_id: str | None = None
    style_family: str | None = None
    era_code: str | None = None
    source_ref: str | None = None
    document_ref: str | None = None
    chunk_ref: str | None = None
    confidence: float = 1.0
    freshness: str | None = None
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    def compact_text(self) -> str:
        body = self.body.strip() if isinstance(self.body, str) else ""
        if body:
            return f"{self.summary.strip()} {body}".strip()
        return self.summary.strip()

    def reference(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "knowledge_type": self.knowledge_type.value,
            "provider_code": self.provider_code,
            "title": self.title,
            "style_id": self.style_id,
            "style_family": self.style_family,
            "era_code": self.era_code,
            "source_ref": self.source_ref,
            "confidence": self.confidence,
            "freshness": self.freshness,
        }

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
