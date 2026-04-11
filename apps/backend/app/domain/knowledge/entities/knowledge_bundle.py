import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from app.domain.knowledge.entities.knowledge_card import KnowledgeCard


class KnowledgeBundle(BaseModel):
    style_cards: list[KnowledgeCard] = Field(default_factory=list)
    color_cards: list[KnowledgeCard] = Field(default_factory=list)
    history_cards: list[KnowledgeCard] = Field(default_factory=list)
    tailoring_cards: list[KnowledgeCard] = Field(default_factory=list)
    materials_cards: list[KnowledgeCard] = Field(default_factory=list)
    flatlay_cards: list[KnowledgeCard] = Field(default_factory=list)
    retrieval_trace: dict[str, Any] = Field(default_factory=dict)

    def all_cards(self) -> list[KnowledgeCard]:
        return [
            *self.style_cards,
            *self.color_cards,
            *self.history_cards,
            *self.tailoring_cards,
            *self.materials_cards,
            *self.flatlay_cards,
        ]

    def is_empty(self) -> bool:
        return not self.all_cards()

    def counts(self) -> dict[str, int]:
        return {
            "retrieved_style_cards_count": len(self.style_cards),
            "retrieved_color_cards_count": len(self.color_cards),
            "retrieved_history_cards_count": len(self.history_cards),
            "retrieved_tailoring_cards_count": len(self.tailoring_cards),
            "retrieved_material_cards_count": len(self.materials_cards),
            "retrieved_flatlay_cards_count": len(self.flatlay_cards),
        }

    def knowledge_refs(self) -> list[dict[str, Any]]:
        return [card.reference() for card in self.all_cards()]

    def content_hash(self) -> str:
        payload = json.dumps(
            {
                "style_cards": [item.model_dump(mode="json") for item in self.style_cards],
                "color_cards": [item.model_dump(mode="json") for item in self.color_cards],
                "history_cards": [item.model_dump(mode="json") for item in self.history_cards],
                "tailoring_cards": [item.model_dump(mode="json") for item in self.tailoring_cards],
                "materials_cards": [item.model_dump(mode="json") for item in self.materials_cards],
                "flatlay_cards": [item.model_dump(mode="json") for item in self.flatlay_cards],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
