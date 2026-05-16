import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from app.domain.knowledge.enums.knowledge_type import KnowledgeType


class KnowledgeChunk(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    knowledge_type: KnowledgeType
    chunk_text: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
