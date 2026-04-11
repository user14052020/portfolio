from app.domain.knowledge.entities import KnowledgeQuery


class DefaultKnowledgeSearchAdapter:
    def expand_terms(self, *, query: KnowledgeQuery) -> list[str]:
        terms: list[str] = []
        for value in (
            query.style_id,
            query.style_name,
            (query.anchor_garment or {}).get("garment_type"),
            (query.anchor_garment or {}).get("material"),
            (query.anchor_garment or {}).get("color_primary"),
            (query.occasion_context or {}).get("event_type"),
            (query.occasion_context or {}).get("dress_code"),
            (query.occasion_context or {}).get("season"),
            (query.occasion_context or {}).get("desired_impression"),
        ):
            if isinstance(value, str) and value.strip():
                terms.append(value.strip().lower())
        return terms
