from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType

from .base import DerivedStyleKnowledgeRepository


class DatabaseFlatlayPatternsRepository(DerivedStyleKnowledgeRepository):
    async def search(self, *, query: KnowledgeQuery, context_style_cards: list[KnowledgeCard] | None = None) -> list[KnowledgeCard]:
        style_cards = await self.resolve_style_cards(query=query, context_style_cards=context_style_cards)
        cards: list[KnowledgeCard] = []
        for style_card in style_cards[: max(query.limit, 4)]:
            metadata = style_card.metadata or {}
            prompt_notes = metadata.get("image_prompt_notes") or []
            composition_cues = metadata.get("composition_cues") or []
            visual_motifs = metadata.get("visual_motifs") or []
            lighting_mood = metadata.get("lighting_mood") or []
            photo_treatment = metadata.get("photo_treatment") or []
            patterns = metadata.get("patterns_textures") or []
            body_bits = [
                str(item).strip()
                for item in [
                    *composition_cues[:3],
                    *prompt_notes[:2],
                    *visual_motifs[:2],
                    *lighting_mood[:1],
                    *photo_treatment[:1],
                    *patterns[:2],
                ]
                if str(item).strip()
            ]
            if not body_bits:
                continue
            cards.append(
                KnowledgeCard(
                    id=f"flatlay:{style_card.style_id or style_card.id}",
                    knowledge_type=KnowledgeType.FLATLAY_PROMPT_PATTERNS,
                    title=f"Flatlay composition for {style_card.title}",
                    summary=body_bits[0],
                    body="; ".join(body_bits[1:]) or None,
                    tags=[*style_card.tags[:8], *patterns[:3]],
                    style_id=style_card.style_id,
                    source_ref=style_card.source_ref,
                    confidence=style_card.confidence,
                    freshness=style_card.freshness,
                    metadata={
                        "image_prompt_notes": list(prompt_notes),
                        "composition_cues": list(composition_cues),
                        "visual_motifs": list(visual_motifs),
                        "style_id": style_card.style_id,
                    },
                )
            )
        return cards
