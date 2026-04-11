from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType

from .base import DerivedStyleKnowledgeRepository


class DatabaseFashionHistoryRepository(DerivedStyleKnowledgeRepository):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        style_cards = await self.resolve_style_cards(query=query, context_style_cards=context_style_cards)
        cards: list[KnowledgeCard] = []
        for style_card in style_cards[: max(query.limit, 3)]:
            historical = style_card.metadata.get("historical_context")
            cultural = style_card.metadata.get("cultural_context")
            if not historical and not cultural:
                continue
            body_bits = [bit for bit in [historical, cultural] if isinstance(bit, str) and bit.strip()]
            cards.append(
                KnowledgeCard(
                    id=f"fashion_history:{style_card.style_id or style_card.id}",
                    knowledge_type=KnowledgeType.FASHION_HISTORY,
                    title=f"History of {style_card.title}",
                    summary=(historical or cultural or style_card.summary).strip(),
                    body=" ".join(body_bits).strip() or None,
                    tags=style_card.tags[:8],
                    style_id=style_card.style_id,
                    source_ref=style_card.source_ref,
                    confidence=style_card.confidence,
                    freshness=style_card.freshness,
                    metadata={"style_id": style_card.style_id},
                )
            )
        return cards
