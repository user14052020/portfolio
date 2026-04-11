from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType

from .base import DerivedStyleKnowledgeRepository


class DatabaseMaterialsFabricsRepository(DerivedStyleKnowledgeRepository):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        style_cards = await self.resolve_style_cards(query=query, context_style_cards=context_style_cards)
        cards: list[KnowledgeCard] = []
        for style_card in style_cards[: max(query.limit, 4)]:
            materials = style_card.metadata.get("materials") or []
            seasonality = style_card.metadata.get("seasonality") or []
            if not materials:
                continue
            cards.append(
                KnowledgeCard(
                    id=f"materials:{style_card.style_id or style_card.id}",
                    knowledge_type=KnowledgeType.MATERIALS_FABRICS,
                    title=f"Materials for {style_card.title}",
                    summary=f"Use {', '.join(str(item) for item in materials[:3])} to keep the style readable.",
                    body=(
                        f"Seasonality: {', '.join(str(item) for item in seasonality[:3])}."
                        if seasonality
                        else None
                    ),
                    tags=[*style_card.tags[:8], *materials[:4]],
                    style_id=style_card.style_id,
                    source_ref=style_card.source_ref,
                    confidence=style_card.confidence,
                    freshness=style_card.freshness,
                    metadata={"materials": list(materials), "seasonality": list(seasonality), "style_id": style_card.style_id},
                )
            )
        return cards
