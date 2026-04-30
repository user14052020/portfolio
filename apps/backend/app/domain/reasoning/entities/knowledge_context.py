from typing import Any

from pydantic import BaseModel, Field

from app.domain.knowledge.entities import KnowledgeCard


class StyleKnowledgeCard(BaseModel):
    style_id: int | str
    title: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    source_ref: str | None = None


class KnowledgeContext(BaseModel):
    providers_used: list[str] = Field(default_factory=list)
    knowledge_cards: list[KnowledgeCard] = Field(default_factory=list)
    style_cards: list[StyleKnowledgeCard] = Field(default_factory=list)
    style_advice_cards: list[KnowledgeCard] = Field(default_factory=list)
    style_visual_cards: list[KnowledgeCard] = Field(default_factory=list)
    style_history_cards: list[KnowledgeCard] = Field(default_factory=list)
    editorial_cards: list[KnowledgeCard] = Field(default_factory=list)
    observability: dict[str, Any] = Field(default_factory=dict)

    def all_cards(self) -> list[KnowledgeCard | StyleKnowledgeCard]:
        return [
            *self.knowledge_cards,
            *self.style_cards,
            *self.style_advice_cards,
            *self.style_visual_cards,
            *self.style_history_cards,
            *self.editorial_cards,
        ]

    def counts(self) -> dict[str, int]:
        return {
            "knowledge_cards": len(self.knowledge_cards),
            "style_cards": len(self.style_cards),
            "style_advice_cards": len(self.style_advice_cards),
            "style_visual_cards": len(self.style_visual_cards),
            "style_history_cards": len(self.style_history_cards),
            "editorial_cards": len(self.editorial_cards),
        }

    def is_empty(self) -> bool:
        return not self.all_cards()
