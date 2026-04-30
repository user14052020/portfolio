from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.knowledge.services.style_facet_knowledge_projector import (
    DefaultStyleFacetKnowledgeProjector,
    StyleFacetProjectionSource,
)
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery, StyleKnowledgeProjectionResult
from app.models import (
    Style,
    StyleAlias,
    StyleFashionItemFacet,
    StyleImageFacet,
    StyleKnowledgeFacet,
    StylePresentationFacet,
    StyleProfile,
    StyleRelation,
    StyleRelationFacet,
    StyleSource,
    StyleTrait,
    StyleVisualFacet,
)


@dataclass(frozen=True)
class _StyleFacetBundle:
    knowledge: StyleKnowledgeFacet | None = None
    visual: StyleVisualFacet | None = None
    fashion: StyleFashionItemFacet | None = None
    image: StyleImageFacet | None = None
    relation: StyleRelationFacet | None = None
    presentation: StylePresentationFacet | None = None


class DatabaseStyleCatalogRepository:
    def __init__(
        self,
        session: AsyncSession,
        *,
        projector: DefaultStyleFacetKnowledgeProjector | None = None,
    ) -> None:
        self.session = session
        self._projector = projector or DefaultStyleFacetKnowledgeProjector()

    async def search(self, *, query: KnowledgeQuery) -> list[KnowledgeCard]:
        projections = await self.search_projections(query=query)
        cards: list[KnowledgeCard] = []
        for projection in projections:
            primary_card = projection.primary_runtime_card()
            if primary_card is not None:
                cards.append(primary_card)
        if query.profile_context:
            cards = self._sort_cards_with_profile_weighting(cards=cards, query=query)
        return cards

    async def search_projections(self, *, query: KnowledgeQuery) -> list[StyleKnowledgeProjectionResult]:
        limit = max(query.limit * 4, 12)
        style_rows = await self._load_style_rows(query=query, limit=limit)
        if not style_rows:
            return []
        style_ids = [style.id for style, _, _ in style_rows]
        aliases = await self._load_aliases(style_ids=style_ids)
        traits = await self._load_traits(style_ids=style_ids)
        relations = await self._load_relations(style_ids=style_ids)
        knowledge_facets = await self._load_latest_facets(StyleKnowledgeFacet, style_ids=style_ids)
        visual_facets = await self._load_latest_facets(StyleVisualFacet, style_ids=style_ids)
        fashion_facets = await self._load_latest_facets(StyleFashionItemFacet, style_ids=style_ids)
        image_facets = await self._load_latest_facets(StyleImageFacet, style_ids=style_ids)
        relation_facets = await self._load_latest_facets(StyleRelationFacet, style_ids=style_ids)
        presentation_facets = await self._load_latest_facets(StylePresentationFacet, style_ids=style_ids)
        return [
            self._build_projection(
                style=style,
                profile=profile,
                source=source,
                aliases=aliases.get(style.id, []),
                traits=traits.get(style.id, []),
                relations=relations.get(style.id, []),
                facets=_StyleFacetBundle(
                    knowledge=knowledge_facets.get(style.id),
                    visual=visual_facets.get(style.id),
                    fashion=fashion_facets.get(style.id),
                    image=image_facets.get(style.id),
                    relation=relation_facets.get(style.id),
                    presentation=presentation_facets.get(style.id),
                ),
            )
            for style, profile, source in style_rows
        ]

    async def list_candidate_styles(
        self,
        *,
        limit: int,
        exclude_style_ids: list[str] | None = None,
    ) -> list[KnowledgeCard]:
        query = KnowledgeQuery(mode="style_exploration", limit=limit)
        cards = await self.search(query=query)
        excluded = {item.strip().lower() for item in (exclude_style_ids or []) if isinstance(item, str) and item.strip()}
        if not excluded:
            return cards[:limit]
        result: list[KnowledgeCard] = []
        for card in cards:
            style_id = (card.style_id or "").strip().lower()
            if style_id and style_id in excluded:
                continue
            result.append(card)
            if len(result) >= limit:
                break
        return result

    async def _load_style_rows(
        self,
        *,
        query: KnowledgeQuery,
        limit: int,
    ) -> list[tuple[Style, StyleProfile | None, StyleSource | None]]:
        alias_style_ids: list[int] = []
        if query.style_name:
            alias_result = await self.session.execute(
                select(StyleAlias.style_id).where(func.lower(StyleAlias.alias).like(f"%{query.style_name.lower()}%"))
            )
            alias_style_ids = list(alias_result.scalars().all())

        statement = (
            select(Style, StyleProfile, StyleSource)
            .outerjoin(StyleProfile, StyleProfile.style_id == Style.id)
            .outerjoin(StyleSource, Style.source_primary_id == StyleSource.id)
        )
        if query.style_id:
            statement = statement.where(Style.slug == query.style_id)
        elif query.style_name:
            lowered = f"%{query.style_name.lower()}%"
            conditions = [
                func.lower(Style.display_name).like(lowered),
                func.lower(Style.canonical_name).like(lowered),
                func.lower(Style.slug).like(lowered),
            ]
            if alias_style_ids:
                conditions.append(Style.id.in_(alias_style_ids))
            statement = statement.where(or_(*conditions))
        statement = statement.where(Style.status != "archived")
        statement = statement.order_by(Style.confidence_score.desc(), Style.display_name.asc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.all())

    async def _load_aliases(self, *, style_ids: list[int]) -> dict[int, list[StyleAlias]]:
        if not style_ids:
            return {}
        result = await self.session.execute(
            select(StyleAlias).where(StyleAlias.style_id.in_(style_ids)).order_by(StyleAlias.is_primary_match_hint.desc())
        )
        grouped: dict[int, list[StyleAlias]] = defaultdict(list)
        for item in result.scalars().all():
            grouped[item.style_id].append(item)
        return grouped

    async def _load_traits(self, *, style_ids: list[int]) -> dict[int, list[StyleTrait]]:
        if not style_ids:
            return {}
        result = await self.session.execute(
            select(StyleTrait)
            .where(StyleTrait.style_id.in_(style_ids))
            .order_by(StyleTrait.weight.desc(), StyleTrait.id.asc())
        )
        grouped: dict[int, list[StyleTrait]] = defaultdict(list)
        for item in result.scalars().all():
            grouped[item.style_id].append(item)
        return grouped

    async def _load_relations(self, *, style_ids: list[int]) -> dict[int, list[StyleRelation]]:
        if not style_ids:
            return {}
        result = await self.session.execute(
            select(StyleRelation)
            .where(StyleRelation.source_style_id.in_(style_ids))
            .order_by(StyleRelation.score.desc(), StyleRelation.id.asc())
        )
        grouped: dict[int, list[StyleRelation]] = defaultdict(list)
        for item in result.scalars().all():
            grouped[item.source_style_id].append(item)
        return grouped

    async def _load_latest_facets(self, model: type[Any], *, style_ids: list[int]) -> dict[int, Any]:
        if not style_ids:
            return {}
        latest_rows = (
            select(
                model.style_id.label("style_id"),
                func.max(model.id).label("latest_id"),
            )
            .where(model.style_id.in_(style_ids))
            .group_by(model.style_id)
            .subquery()
        )
        result = await self.session.execute(
            select(model).join(latest_rows, model.id == latest_rows.c.latest_id)
        )
        return {item.style_id: item for item in result.scalars().all()}

    def _build_projection(
        self,
        *,
        style: Style,
        profile: StyleProfile | None,
        source: StyleSource | None,
        aliases: list[StyleAlias],
        traits: list[StyleTrait],
        relations: list[StyleRelation],
        facets: _StyleFacetBundle,
    ) -> KnowledgeCard:
        projection = self._projector.project_from_source(
            source=StyleFacetProjectionSource(
                style=style,
                profile=profile,
                source=source,
                aliases=aliases,
                traits=traits,
                relations=relations,
                knowledge_facet=facets.knowledge,
                visual_facet=facets.visual,
                fashion_facet=facets.fashion,
                image_facet=facets.image,
                relation_facet=facets.relation,
                presentation_facet=facets.presentation,
            )
        )
        primary_card = projection.primary_runtime_card()
        if primary_card is None:
            raise ValueError(f"Projection for style {style.slug} produced no runtime card")
        return projection

    def _sort_cards_with_profile_weighting(
        self,
        *,
        cards: list[KnowledgeCard],
        query: KnowledgeQuery,
    ) -> list[KnowledgeCard]:
        return sorted(
            cards,
            key=lambda card: self._profile_weighted_score(card=card, query=query),
            reverse=True,
        )

    def _profile_weighted_score(self, *, card: KnowledgeCard, query: KnowledgeQuery) -> float:
        score = float(card.confidence)
        profile = query.profile_context or {}
        haystack = self._card_profile_haystack(card)

        score += 1.2 * self._term_overlap_score(haystack, [profile.get("presentation_profile")])
        score += 1.0 * self._term_overlap_score(haystack, profile.get("fit_preferences"))
        score += 1.15 * self._term_overlap_score(haystack, profile.get("silhouette_preferences"))
        score += 0.75 * self._term_overlap_score(haystack, profile.get("comfort_preferences"))
        score += 0.8 * self._term_overlap_score(haystack, profile.get("formality_preferences"))
        score += 0.7 * self._term_overlap_score(haystack, profile.get("color_preferences"))
        score += 0.9 * self._term_overlap_score(haystack, profile.get("preferred_items"))

        score -= 1.35 * self._term_overlap_score(haystack, profile.get("avoided_items"))
        score -= 1.0 * self._term_overlap_score(haystack, profile.get("color_avoidances"))
        return score

    def _card_profile_haystack(self, card: KnowledgeCard) -> set[str]:
        metadata = card.metadata or {}
        values: list[Any] = [
            card.title,
            card.summary,
            card.body or "",
            *card.tags,
            metadata.get("style_name"),
            metadata.get("style_slug"),
            metadata.get("fashion_summary"),
            metadata.get("visual_summary"),
            metadata.get("presentation_short_explanation"),
            metadata.get("presentation_one_sentence_description"),
            metadata.get("historical_context"),
            metadata.get("cultural_context"),
            metadata.get("silhouette_family"),
            metadata.get("palette"),
            metadata.get("hero_garments"),
            metadata.get("secondary_garments"),
            metadata.get("garments"),
            metadata.get("materials"),
            metadata.get("footwear"),
            metadata.get("accessories"),
            metadata.get("mood_keywords"),
            metadata.get("patterns_textures"),
            metadata.get("styling_rules"),
            metadata.get("casual_adaptations"),
            metadata.get("statement_pieces"),
            metadata.get("status_markers"),
            metadata.get("platform_visual_cues"),
            metadata.get("tops"),
            metadata.get("bottoms"),
            metadata.get("shoes"),
            metadata.get("signature_details"),
            metadata.get("props"),
            metadata.get("related_styles"),
            metadata.get("overlap_styles"),
            metadata.get("brands"),
            metadata.get("platforms"),
            metadata.get("origin_regions"),
            metadata.get("era"),
        ]
        return {
            token
            for value in values
            for token in self._tokenize_profile_value(value)
        }

    def _term_overlap_score(self, haystack: set[str], raw_values: Any) -> float:
        score = 0.0
        for term in self._tokenize_profile_value(raw_values):
            if term in haystack:
                score += 1.0
        return score

    def _tokenize_profile_value(self, raw_values: Any) -> list[str]:
        items: list[str] = []
        if isinstance(raw_values, str):
            items = [raw_values]
        elif isinstance(raw_values, (list, tuple, set)):
            items = [str(item) for item in raw_values]
        elif raw_values is not None:
            items = [str(raw_values)]

        tokens: list[str] = []
        seen: set[str] = set()
        for item in items:
            normalized = item.replace("_", " ").replace("-", " ").strip().lower()
            if not normalized:
                continue
            variants = {normalized, normalized.replace(" ", "_"), normalized.replace(" ", "-")}
            for variant in variants:
                if variant and variant not in seen:
                    seen.add(variant)
                    tokens.append(variant)
        return tokens

    def _trait_map(self, traits: list[StyleTrait]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for trait in traits:
            grouped[trait.trait_type].append(trait.trait_value)
        return dict(grouped)

    def _unique_strings(self, values: list[Any]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value).strip()
            lowered = cleaned.lower()
            if not cleaned or lowered in seen:
                continue
            seen.add(lowered)
            result.append(cleaned)
        return result

    def _first_non_empty_text(self, *values: Any) -> str:
        for value in values:
            if not isinstance(value, str):
                continue
            cleaned = " ".join(value.split()).strip()
            if cleaned:
                return cleaned
        return ""

    def _first_non_empty_list(self, *values: list[Any]) -> list[str]:
        for value in values:
            items = self._merge_unique_strings(value)
            if items:
                return items
        return []

    def _merge_unique_strings(self, *values: Any) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if isinstance(value, str):
                iterable = [value]
            elif isinstance(value, (list, tuple, set)):
                iterable = list(value)
            else:
                iterable = []
            for item in iterable:
                cleaned = " ".join(str(item).split()).strip()
                lowered = cleaned.lower()
                if not cleaned or lowered in seen:
                    continue
                seen.add(lowered)
                result.append(cleaned)
        return result

    def _join_text_segments(self, *values: Any) -> str | None:
        parts = self._merge_unique_strings(*values)
        if not parts:
            return None
        return "; ".join(parts[:6])
