from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType

from .base import DerivedStyleKnowledgeRepository


class DatabaseFashionHistoryRepository(DerivedStyleKnowledgeRepository):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        style_cards = await self.resolve_style_cards(query=query, context_style_cards=context_style_cards)
        cards: list[KnowledgeCard] = []
        for style_card in style_cards[: max(query.limit, 3)]:
            metadata = style_card.metadata or {}
            historical_notes = [str(item).strip() for item in metadata.get("historical_notes", []) if str(item).strip()]
            overlap_context = [str(item).strip() for item in metadata.get("overlap_context", []) if str(item).strip()]
            era = [str(item).strip() for item in metadata.get("era", []) if str(item).strip()]
            origin_regions = [str(item).strip() for item in metadata.get("origin_regions", []) if str(item).strip()]
            historical = metadata.get("historical_context")
            cultural = metadata.get("cultural_context")
            summary_bits = historical_notes[:2] or ([historical] if isinstance(historical, str) and historical.strip() else [])
            body_bits = [
                *historical_notes[2:5],
                *overlap_context[:2],
                *era[:2],
                *origin_regions[:2],
            ]
            if not summary_bits and not body_bits and not cultural:
                continue
            cards.append(
                KnowledgeCard(
                    id=f"fashion_history:{style_card.style_id or style_card.id}",
                    knowledge_type=KnowledgeType.FASHION_HISTORY,
                    title=f"History of {style_card.title}",
                    summary="; ".join(summary_bits) if summary_bits else (cultural or style_card.summary).strip(),
                    body="; ".join([*body_bits, cultural] if isinstance(cultural, str) and cultural.strip() else body_bits).strip() or None,
                    tags=style_card.tags[:8],
                    style_id=style_card.style_id,
                    source_ref=style_card.source_ref,
                    confidence=style_card.confidence,
                    freshness=style_card.freshness,
                    metadata={
                        "style_id": style_card.style_id,
                        "historical_notes": historical_notes,
                        "overlap_context": overlap_context,
                        "era": era,
                        "origin_regions": origin_regions,
                    },
                )
            )
        return cards
