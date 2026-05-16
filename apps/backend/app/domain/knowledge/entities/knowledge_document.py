import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeDocument(BaseModel):
    id: str
    provider_code: str
    title: str
    author: str | None = None
    source_ref: str | None = None
    language: str = "en"
    raw_text: str
    clean_text: str
    version: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def content_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
