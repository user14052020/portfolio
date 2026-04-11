from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType

from .base import DerivedStyleKnowledgeRepository


class DatabaseColorTheoryRepository(DerivedStyleKnowledgeRepository):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        style_cards = await self.resolve_style_cards(query=query, context_style_cards=context_style_cards)
        cards: list[KnowledgeCard] = []
        for style_card in style_cards[: max(query.limit, 3)]:
            palette = style_card.metadata.get("palette") or []
            if not palette:
                continue
            cards.append(
                KnowledgeCard(
                    id=f"color_theory:{style_card.style_id or style_card.id}",
                    knowledge_type=KnowledgeType.COLOR_THEORY,
                    title=f"Color logic for {style_card.title}",
                    summary=f"Build the palette around {', '.join(str(item) for item in palette[:3])}.",
                    body=(
                        style_card.metadata.get("fashion_summary")
                        or style_card.metadata.get("visual_summary")
                        or style_card.summary
                    ),
                    tags=[*style_card.tags[:6], *palette[:4]],
                    style_id=style_card.style_id,
                    source_ref=style_card.source_ref,
                    confidence=style_card.confidence,
                    freshness=style_card.freshness,
                    metadata={"palette": list(palette), "style_id": style_card.style_id},
                )
            )
        return cards
