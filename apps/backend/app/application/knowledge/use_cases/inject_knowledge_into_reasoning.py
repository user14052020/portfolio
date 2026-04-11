from dataclasses import dataclass
from typing import Any

from app.application.stylist_chat.contracts.ports import KnowledgeItem, KnowledgeResult
from app.domain.knowledge.entities import KnowledgeBundle, KnowledgeCard
from app.domain.knowledge.enums import KnowledgeType


@dataclass(slots=True)
class InjectedKnowledge:
    bundle: KnowledgeBundle
    knowledge_cards: list[dict[str, Any]]
    knowledge_result: KnowledgeResult
    refs: list[dict[str, Any]]


class InjectKnowledgeIntoReasoningUseCase:
    def execute(self, *, bundle: KnowledgeBundle) -> InjectedKnowledge:
        flattened_cards = [self._card_payload(card=card) for card in bundle.all_cards()]
        knowledge_result = KnowledgeResult(
            items=[KnowledgeItem(card["key"], card["text"]) for card in flattened_cards],
            source="knowledge_layer",
            query=dict(bundle.retrieval_trace),
        )
        return InjectedKnowledge(
            bundle=bundle,
            knowledge_cards=flattened_cards,
            knowledge_result=knowledge_result,
            refs=bundle.knowledge_refs(),
        )

    def _card_payload(self, *, card: KnowledgeCard) -> dict[str, Any]:
        return {
            "key": self._key_for_type(card.knowledge_type),
            "text": card.compact_text(),
            "knowledge_type": card.knowledge_type.value,
            "title": card.title,
            "style_id": card.style_id,
            "source_ref": card.source_ref,
            "confidence": card.confidence,
            "freshness": card.freshness,
            "tags": list(card.tags),
            "metadata": dict(card.metadata),
        }

    def _key_for_type(self, knowledge_type: KnowledgeType) -> str:
        mapping = {
            KnowledgeType.STYLE_CATALOG: "style_catalog",
            KnowledgeType.COLOR_THEORY: "color",
            KnowledgeType.FASHION_HISTORY: "history",
            KnowledgeType.TAILORING_PRINCIPLES: "tailoring",
            KnowledgeType.MATERIALS_FABRICS: "materials",
            KnowledgeType.FLATLAY_PROMPT_PATTERNS: "flatlay",
        }
        return mapping[knowledge_type]
