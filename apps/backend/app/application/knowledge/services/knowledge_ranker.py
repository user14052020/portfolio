from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery


class KnowledgeRanker:
    def rank(self, *, cards: list[KnowledgeCard], query: KnowledgeQuery) -> list[KnowledgeCard]:
        return sorted(cards, key=lambda item: self._score(card=item, query=query), reverse=True)

    def _score(self, *, card: KnowledgeCard, query: KnowledgeQuery) -> float:
        haystack = " ".join(
            [
                card.title,
                card.summary,
                card.body or "",
                " ".join(card.tags),
                " ".join(str(value) for value in card.metadata.values() if isinstance(value, str)),
            ]
        ).lower()
        score = float(card.confidence)
        if query.style_id and card.style_id == query.style_id:
            score += 6.0
        if query.style_name and query.style_name.lower() in haystack:
            score += 4.0
        anchor = query.anchor_garment or {}
        for key, weight in (("garment_type", 2.5), ("material", 1.75), ("color_primary", 1.25), ("fit", 1.0)):
            value = anchor.get(key)
            if isinstance(value, str) and value.strip() and value.strip().lower() in haystack:
                score += weight
        occasion = query.occasion_context or {}
        for key, weight in (
            ("event_type", 2.5),
            ("dress_code", 2.0),
            ("desired_impression", 1.25),
            ("season", 1.0),
            ("season_or_weather", 1.0),
            ("weather_context", 0.75),
            ("time_of_day", 0.75),
        ):
            value = occasion.get(key)
            if isinstance(value, str) and value.strip() and value.strip().lower() in haystack:
                score += weight
        constraints = query.diversity_constraints or {}
        score -= self._diversity_penalty(card=card, constraints=constraints)
        return score

    def _diversity_penalty(self, *, card: KnowledgeCard, constraints: dict[str, object]) -> float:
        penalty = 0.0
        metadata = card.metadata or {}
        for field_name, constraint_key, weight in (
            ("palette", "avoid_palette", 1.5),
            ("hero_garments", "avoid_hero_garments", 1.75),
            ("silhouette_family", "avoid_silhouette_families", 1.25),
            ("materials", "avoid_materials", 1.0),
        ):
            current_values = metadata.get(field_name)
            avoid_values = constraints.get(constraint_key)
            if not isinstance(avoid_values, list) or not avoid_values:
                continue
            if isinstance(current_values, str):
                current_values = [current_values]
            if not isinstance(current_values, list):
                continue
            current = {str(item).strip().lower() for item in current_values if str(item).strip()}
            avoid = {str(item).strip().lower() for item in avoid_values if str(item).strip()}
            if current & avoid:
                penalty += weight
        return penalty
