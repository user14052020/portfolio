from app.domain.knowledge.entities import KnowledgeBundle, KnowledgeCard, KnowledgeQuery


class KnowledgeBundleBuilder:
    def build(
        self,
        *,
        query: KnowledgeQuery,
        style_cards: list[KnowledgeCard],
        color_cards: list[KnowledgeCard],
        history_cards: list[KnowledgeCard],
        tailoring_cards: list[KnowledgeCard],
        materials_cards: list[KnowledgeCard],
        flatlay_cards: list[KnowledgeCard],
    ) -> KnowledgeBundle:
        bundle = KnowledgeBundle(
            style_cards=style_cards[: query.limit],
            color_cards=color_cards[: query.limit],
            history_cards=history_cards[: query.limit],
            tailoring_cards=tailoring_cards[: query.limit],
            materials_cards=materials_cards[: query.limit],
            flatlay_cards=flatlay_cards[: query.limit],
        )
        bundle_hash = bundle.content_hash()
        bundle.retrieval_trace = {
            "mode": query.mode,
            "intent": query.intent,
            "style_id": query.style_id,
            "style_name": query.style_name,
            "knowledge_query_hash": query.content_hash(),
            "knowledge_bundle_hash": bundle_hash,
            **bundle.counts(),
        }
        return bundle
