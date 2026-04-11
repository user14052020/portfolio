from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType

from .base import DerivedStyleKnowledgeRepository


class DatabaseTailoringPrinciplesRepository(DerivedStyleKnowledgeRepository):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        style_cards = await self.resolve_style_cards(query=query, context_style_cards=context_style_cards)
        cards: list[KnowledgeCard] = []
        for style_card in style_cards[: max(query.limit, 4)]:
            silhouette = style_card.metadata.get("silhouette_family")
            styling_advice = style_card.metadata.get("styling_advice") or []
            occasion_fit = style_card.metadata.get("occasion_fit") or []
            summary_bits = [bit for bit in [silhouette, *styling_advice[:2], *occasion_fit[:1]] if isinstance(bit, str) and bit.strip()]
            if not summary_bits:
                continue
            cards.append(
                KnowledgeCard(
                    id=f"tailoring:{style_card.style_id or style_card.id}",
                    knowledge_type=KnowledgeType.TAILORING_PRINCIPLES,
                    title=f"Tailoring logic for {style_card.title}",
                    summary="; ".join(summary_bits[:3]),
                    body="; ".join(str(item).strip() for item in styling_advice[2:5] if str(item).strip()) or None,
                    tags=[*style_card.tags[:8], *(style_card.metadata.get("silhouettes") or [])[:3]],
                    style_id=style_card.style_id,
                    source_ref=style_card.source_ref,
                    confidence=style_card.confidence,
                    freshness=style_card.freshness,
                    metadata={
                        "silhouette_family": silhouette,
                        "occasion_fit": list(occasion_fit),
                        "style_id": style_card.style_id,
                    },
                )
            )
        return cards
