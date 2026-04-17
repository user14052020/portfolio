from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType

from .base import DerivedStyleKnowledgeRepository


class DatabaseMaterialsFabricsRepository(DerivedStyleKnowledgeRepository):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        style_cards = await self.resolve_style_cards(query=query, context_style_cards=context_style_cards)
        cards: list[KnowledgeCard] = []
        for style_card in style_cards[: max(query.limit, 4)]:
            metadata = style_card.metadata or {}
            materials = metadata.get("materials") or []
            seasonality = metadata.get("seasonality") or []
            textures = metadata.get("patterns_textures") or []
            signature_details = metadata.get("signature_details") or []
            if not materials:
                continue
            cards.append(
                KnowledgeCard(
                    id=f"materials:{style_card.style_id or style_card.id}",
                    knowledge_type=KnowledgeType.MATERIALS_FABRICS,
                    title=f"Materials for {style_card.title}",
                    summary=f"Use {', '.join(str(item) for item in materials[:3])} to keep the style readable.",
                    body=(
                        "; ".join(
                            bit
                            for bit in [
                                f"Seasonality: {', '.join(str(item) for item in seasonality[:3])}" if seasonality else "",
                                f"Textures: {', '.join(str(item) for item in textures[:3])}" if textures else "",
                                f"Signature details: {', '.join(str(item) for item in signature_details[:2])}" if signature_details else "",
                            ]
                            if bit
                        )
                        if seasonality or textures or signature_details
                        else None
                    ),
                    tags=[*style_card.tags[:8], *materials[:4], *textures[:3]],
                    style_id=style_card.style_id,
                    source_ref=style_card.source_ref,
                    confidence=style_card.confidence,
                    freshness=style_card.freshness,
                    metadata={
                        "materials": list(materials),
                        "seasonality": list(seasonality),
                        "patterns_textures": list(textures),
                        "signature_details": list(signature_details),
                        "style_id": style_card.style_id,
                    },
                )
            )
        return cards
