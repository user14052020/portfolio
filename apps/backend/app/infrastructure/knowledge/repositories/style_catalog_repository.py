from collections import defaultdict
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType
from app.models import Style, StyleAlias, StyleProfile, StyleRelation, StyleSource, StyleTrait


class DatabaseStyleCatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, *, query: KnowledgeQuery) -> list[KnowledgeCard]:
        limit = max(query.limit * 4, 12)
        style_rows = await self._load_style_rows(query=query, limit=limit)
        if not style_rows:
            return []
        style_ids = [style.id for style, _, _ in style_rows]
        aliases = await self._load_aliases(style_ids=style_ids)
        traits = await self._load_traits(style_ids=style_ids)
        relations = await self._load_relations(style_ids=style_ids)
        return [
            self._build_card(
                style=style,
                profile=profile,
                source=source,
                aliases=aliases.get(style.id, []),
                traits=traits.get(style.id, []),
                relations=relations.get(style.id, []),
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

    def _build_card(
        self,
        *,
        style: Style,
        profile: StyleProfile | None,
        source: StyleSource | None,
        aliases: list[StyleAlias],
        traits: list[StyleTrait],
        relations: list[StyleRelation],
    ) -> KnowledgeCard:
        palette = list(profile.color_palette_json) if profile is not None else []
        garments = list(profile.garments_json) if profile is not None else []
        materials = list(profile.materials_json) if profile is not None else []
        footwear = list(profile.footwear_json) if profile is not None else []
        accessories = list(profile.accessories_json) if profile is not None else []
        silhouettes = list(profile.silhouettes_json) if profile is not None else []
        occasion_fit = list(profile.occasion_fit_json) if profile is not None else []
        seasonality = list(profile.seasonality_json) if profile is not None else []
        image_prompt_notes = list(profile.image_prompt_notes_json) if profile is not None else []
        styling_advice = list(profile.styling_advice_json) if profile is not None else []
        mood_keywords = list(profile.mood_keywords_json) if profile is not None else []
        patterns_textures = list(profile.patterns_textures_json) if profile is not None else []
        alias_values = [item.alias for item in aliases]
        trait_values = [item.trait_value for item in traits]
        summary = style.short_definition or (profile.fashion_summary if profile is not None else None) or style.display_name
        body = style.long_summary or (profile.visual_summary if profile is not None else None)
        metadata: dict[str, Any] = {
            "style_slug": style.slug,
            "style_name": style.display_name,
            "canonical_name": style.canonical_name,
            "palette": palette,
            "hero_garments": garments[:4],
            "garments": garments,
            "materials": materials,
            "footwear": footwear,
            "accessories": accessories,
            "silhouette_family": silhouettes[0] if silhouettes else None,
            "silhouettes": silhouettes,
            "occasion_fit": occasion_fit,
            "seasonality": seasonality,
            "mood_keywords": mood_keywords,
            "patterns_textures": patterns_textures,
            "negative_constraints": list(profile.negative_constraints_json) if profile is not None else [],
            "styling_advice": styling_advice,
            "historical_context": profile.historical_context if profile is not None else None,
            "cultural_context": profile.cultural_context if profile is not None else None,
            "fashion_summary": profile.fashion_summary if profile is not None else None,
            "visual_summary": profile.visual_summary if profile is not None else None,
            "image_prompt_notes": image_prompt_notes,
            "relations": [
                {
                    "target_style_id": relation.target_style_id,
                    "relation_type": relation.relation_type,
                    "score": relation.score,
                }
                for relation in relations[:6]
            ],
            "trait_map": self._trait_map(traits),
        }
        return KnowledgeCard(
            id=f"style_catalog:{style.slug}",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            title=style.display_name,
            summary=summary.strip(),
            body=body.strip() if isinstance(body, str) and body.strip() else None,
            tags=self._unique_strings(
                [
                    style.slug,
                    style.display_name,
                    style.canonical_name,
                    *alias_values,
                    *palette,
                    *garments,
                    *materials,
                    *footwear,
                    *accessories,
                    *silhouettes,
                    *occasion_fit,
                    *seasonality,
                    *mood_keywords,
                    *trait_values,
                ]
            ),
            style_id=style.slug,
            source_ref=source.source_url if source is not None else None,
            confidence=max(style.confidence_score, 0.1),
            freshness=(
                source.last_seen_at.date().isoformat()
                if source is not None and source.last_seen_at is not None
                else style.first_ingested_at.date().isoformat()
            ),
            metadata=metadata,
        )

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
