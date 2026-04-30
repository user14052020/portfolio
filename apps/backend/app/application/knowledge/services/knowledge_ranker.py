from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType


class KnowledgeRanker:
    async def rank(self, *, cards: list[KnowledgeCard], query: KnowledgeQuery) -> list[KnowledgeCard]:
        if not cards:
            return []
        base_scores = {card.id: self._score(card=card, query=query) for card in cards}
        candidates = sorted(
            cards,
            key=lambda item: (
                -base_scores[item.id],
                self._priority_value(item),
                item.knowledge_type.value,
                item.id,
            ),
        )
        selected: list[KnowledgeCard] = []
        remaining = list(candidates)
        while remaining:
            best = max(
                remaining,
                key=lambda item: (
                    base_scores[item.id] - self._selection_diversity_penalty(card=item, selected=selected, query=query),
                    -self._priority_value(item),
                ),
            )
            selected.append(best)
            remaining.remove(best)
        return selected

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
        score += self._knowledge_type_bonus(card=card, query=query)
        score += self._provider_priority_bonus(card=card)
        constraints = query.diversity_constraints or {}
        score -= self._diversity_penalty(card=card, constraints=constraints)
        score += self._profile_weight_bonus(card=card, query=query, haystack=haystack)
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

    def _profile_weight_bonus(self, *, card: KnowledgeCard, query: KnowledgeQuery, haystack: str) -> float:
        profile = query.profile_context or {}
        if not profile:
            return 0.0

        bonus = 0.0
        bonus += 0.9 * self._term_overlap_score(haystack, [profile.get("presentation_profile")])
        bonus += 0.85 * self._term_overlap_score(haystack, profile.get("fit_preferences"))
        bonus += 0.95 * self._term_overlap_score(haystack, profile.get("silhouette_preferences"))
        bonus += 0.8 * self._term_overlap_score(haystack, profile.get("comfort_preferences"))
        bonus += 0.8 * self._term_overlap_score(haystack, profile.get("formality_preferences"))
        bonus += 0.7 * self._term_overlap_score(haystack, profile.get("color_preferences"))
        bonus += 0.7 * self._term_overlap_score(haystack, profile.get("preferred_items"))

        bonus -= 1.0 * self._term_overlap_score(haystack, profile.get("avoided_items"))
        bonus -= 0.75 * self._term_overlap_score(haystack, profile.get("color_avoidances"))
        return bonus

    def _term_overlap_score(self, haystack: str, values: object) -> float:
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            return 0.0

        score = 0.0
        seen: set[str] = set()
        for raw in values:
            term = str(raw).strip().lower()
            if not term or term in seen:
                continue
            seen.add(term)
            if term in haystack:
                score += 1.0
        return score

    def _knowledge_type_bonus(self, *, card: KnowledgeCard, query: KnowledgeQuery) -> float:
        knowledge_type = card.knowledge_type
        bonus = 0.0
        if query.need_styling_rules and knowledge_type in _STYLING_TYPES:
            bonus += 1.2
        if query.need_visual_knowledge and knowledge_type in _VISUAL_TYPES:
            bonus += 1.2
        if query.need_historical_knowledge and knowledge_type in _HISTORICAL_TYPES:
            bonus += 1.0
        if query.need_color_poetics and knowledge_type in _COLOR_TYPES:
            bonus += 0.9
        return bonus

    def _provider_priority_bonus(self, *, card: KnowledgeCard) -> float:
        priority = self._priority_value(card)
        clamped = min(max(priority, 0), 100)
        return ((100 - clamped) / 100.0) * 1.5

    def _selection_diversity_penalty(
        self,
        *,
        card: KnowledgeCard,
        selected: list[KnowledgeCard],
        query: KnowledgeQuery,
    ) -> float:
        if not selected:
            return 0.0

        penalty = 0.0
        provider_code = (card.provider_code or "").strip().lower()
        if provider_code:
            same_provider = sum(
                1
                for item in selected
                if (item.provider_code or "").strip().lower() == provider_code
            )
            penalty += same_provider * 0.25

        same_type = sum(1 for item in selected if item.knowledge_type == card.knowledge_type)
        penalty += same_type * 0.75

        if not query.style_id and card.style_id:
            style_id = card.style_id.strip().lower()
            same_style = sum(
                1
                for item in selected
                if isinstance(item.style_id, str) and item.style_id.strip().lower() == style_id
            )
            penalty += same_style * 0.45

        duplicate_title = sum(
            1
            for item in selected
            if item.title.strip().lower() == card.title.strip().lower()
        )
        penalty += duplicate_title * 1.0
        return penalty

    def _priority_value(self, card: KnowledgeCard) -> int:
        if isinstance(card.provider_priority, int):
            return card.provider_priority
        return 100


_STYLING_TYPES = {
    KnowledgeType.STYLE_STYLING_RULES,
    KnowledgeType.STYLE_CASUAL_ADAPTATIONS,
    KnowledgeType.STYLE_SIGNATURE_DETAILS,
    KnowledgeType.STYLE_NEGATIVE_GUIDANCE,
    KnowledgeType.STYLING_RULES,
    KnowledgeType.TAILORING_PRINCIPLES,
    KnowledgeType.OCCASION_RULES,
}

_VISUAL_TYPES = {
    KnowledgeType.STYLE_VISUAL_LANGUAGE,
    KnowledgeType.STYLE_IMAGE_COMPOSITION,
    KnowledgeType.STYLE_PROPS,
    KnowledgeType.STYLE_PALETTE_LOGIC,
    KnowledgeType.STYLE_PHOTO_TREATMENT,
    KnowledgeType.FLATLAY_PROMPT_PATTERNS,
    KnowledgeType.COMPOSITION_THEORY,
    KnowledgeType.LIGHT_THEORY,
}

_HISTORICAL_TYPES = {
    KnowledgeType.STYLE_RELATION_CONTEXT,
    KnowledgeType.STYLE_BRANDS_PLATFORMS,
    KnowledgeType.FASHION_HISTORY,
    KnowledgeType.STYLE_HISTORY,
}

_COLOR_TYPES = {
    KnowledgeType.COLOR_THEORY,
    KnowledgeType.STYLE_PALETTE_LOGIC,
}
