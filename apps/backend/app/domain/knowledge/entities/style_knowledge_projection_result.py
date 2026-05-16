from pydantic import BaseModel, Field

from app.domain.knowledge.entities.knowledge_card import KnowledgeCard
from app.domain.knowledge.entities.knowledge_chunk import KnowledgeChunk
from app.domain.knowledge.entities.knowledge_document import KnowledgeDocument
from app.domain.knowledge.enums.knowledge_type import KnowledgeType


class StyleKnowledgeProjectionResult(BaseModel):
    provider_code: str
    style_id: int
    style_slug: str
    style_name: str
    projection_version: str
    parser_version: str | None = None
    normalizer_version: str | None = None
    facet_version: str | None = None
    documents: list[KnowledgeDocument] = Field(default_factory=list)
    chunks: list[KnowledgeChunk] = Field(default_factory=list)
    cards: list[KnowledgeCard] = Field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "documents": len(self.documents),
            "chunks": len(self.chunks),
            "cards": len(self.cards),
        }

    def primary_runtime_card(self) -> KnowledgeCard | None:
        preferred_order = (
            KnowledgeType.STYLE_CATALOG,
            KnowledgeType.STYLE_DESCRIPTION,
            KnowledgeType.STYLE_STYLING_RULES,
        )
        for knowledge_type in preferred_order:
            for card in self.cards:
                if card.knowledge_type == knowledge_type and card.is_active:
                    return card
        for card in self.cards:
            if card.is_active:
                return card
        return None
