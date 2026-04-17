from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType
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
        knowledge_facets = await self._load_latest_facets(StyleKnowledgeFacet, style_ids=style_ids)
        visual_facets = await self._load_latest_facets(StyleVisualFacet, style_ids=style_ids)
        fashion_facets = await self._load_latest_facets(StyleFashionItemFacet, style_ids=style_ids)
        image_facets = await self._load_latest_facets(StyleImageFacet, style_ids=style_ids)
        relation_facets = await self._load_latest_facets(StyleRelationFacet, style_ids=style_ids)
        presentation_facets = await self._load_latest_facets(StylePresentationFacet, style_ids=style_ids)
        return [
            self._build_card(
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

    def _build_card(
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
        legacy_palette = list(profile.color_palette_json or []) if profile is not None else []
        legacy_garments = list(profile.garments_json or []) if profile is not None else []
        legacy_materials = list(profile.materials_json or []) if profile is not None else []
        legacy_footwear = list(profile.footwear_json or []) if profile is not None else []
        legacy_accessories = list(profile.accessories_json or []) if profile is not None else []
        silhouettes = list(profile.silhouettes_json or []) if profile is not None else []
        occasion_fit = list(profile.occasion_fit_json or []) if profile is not None else []
        seasonality = list(profile.seasonality_json or []) if profile is not None else []
        legacy_image_prompt_notes = list(profile.image_prompt_notes_json or []) if profile is not None else []
        legacy_styling_advice = list(profile.styling_advice_json or []) if profile is not None else []
        legacy_mood_keywords = list(profile.mood_keywords_json or []) if profile is not None else []
        legacy_patterns_textures = list(profile.patterns_textures_json or []) if profile is not None else []
        legacy_negative_constraints = list(profile.negative_constraints_json or []) if profile is not None else []

        knowledge = facets.knowledge
        visual = facets.visual
        fashion = facets.fashion
        image = facets.image
        relation_facet = facets.relation
        presentation = facets.presentation

        palette = self._first_non_empty_list(
            list(visual.palette_json) if visual is not None else [],
            legacy_palette,
        )
        hero_garments = self._first_non_empty_list(
            list(image.hero_garments_json) if image is not None else [],
            legacy_garments[:4],
        )
        garments = self._merge_unique_strings(
            hero_garments,
            list(image.secondary_garments_json) if image is not None else [],
            list(fashion.tops_json) if fashion is not None else [],
            list(fashion.bottoms_json) if fashion is not None else [],
            legacy_garments,
        )
        materials = self._first_non_empty_list(
            list(image.materials_json) if image is not None else [],
            legacy_materials,
        )
        footwear = self._first_non_empty_list(
            list(fashion.shoes_json) if fashion is not None else [],
            legacy_footwear,
        )
        accessories = self._merge_unique_strings(
            list(image.core_accessories_json) if image is not None else [],
            list(fashion.accessories_json) if fashion is not None else [],
            legacy_accessories,
        )
        styling_advice = self._merge_unique_strings(
            list(knowledge.styling_rules_json) if knowledge is not None else [],
            list(knowledge.casual_adaptations_json) if knowledge is not None else [],
            legacy_styling_advice,
        )
        mood_keywords = self._merge_unique_strings(
            list(visual.visual_motifs_json) if visual is not None else [],
            list(visual.lighting_mood_json) if visual is not None else [],
            list(visual.photo_treatment_json) if visual is not None else [],
            legacy_mood_keywords,
        )
        patterns_textures = self._first_non_empty_list(
            list(visual.patterns_textures_json) if visual is not None else [],
            legacy_patterns_textures,
        )
        negative_constraints = self._merge_unique_strings(
            list(image.negative_constraints_json) if image is not None else [],
            list(knowledge.negative_guidance_json) if knowledge is not None else [],
            legacy_negative_constraints,
        )
        historical_context = self._join_text_segments(
            list(knowledge.historical_notes_json) if knowledge is not None else [],
            [profile.historical_context] if profile is not None else [],
        )
        cultural_context = self._join_text_segments(
            list(relation_facet.origin_regions_json) if relation_facet is not None else [],
            list(relation_facet.platforms_json) if relation_facet is not None else [],
            list(relation_facet.brands_json) if relation_facet is not None else [],
            list(relation_facet.era_json) if relation_facet is not None else [],
            [profile.cultural_context] if profile is not None else [],
        )
        image_prompt_notes = self._merge_unique_strings(
            list(image.composition_cues_json) if image is not None else [],
            list(image.visual_motifs_json) if image is not None else [],
            list(image.lighting_mood_json) if image is not None else [],
            list(image.photo_treatment_json) if image is not None else [],
            legacy_image_prompt_notes,
        )
        alias_values = [item.alias for item in aliases]
        trait_values = [item.trait_value for item in traits]
        summary = self._first_non_empty_text(
            presentation.short_explanation if presentation is not None else None,
            presentation.one_sentence_description if presentation is not None else None,
            knowledge.core_definition if knowledge is not None else None,
            style.short_definition,
            profile.fashion_summary if profile is not None else None,
            profile.visual_summary if profile is not None else None,
            style.display_name,
        )
        body = self._first_non_empty_text(
            self._join_text_segments(
                list(presentation.what_makes_it_distinct_json) if presentation is not None else [],
                list(knowledge.core_style_logic_json) if knowledge is not None else [],
                list(knowledge.styling_rules_json) if knowledge is not None else [],
                list(knowledge.historical_notes_json) if knowledge is not None else [],
                list(visual.visual_motifs_json) if visual is not None else [],
            ),
            style.long_summary,
            profile.visual_summary if profile is not None else None,
        ) or None
        metadata: dict[str, Any] = {
            "style_slug": style.slug,
            "style_name": style.display_name,
            "canonical_name": style.canonical_name,
            "palette": palette,
            "hero_garments": hero_garments,
            "secondary_garments": list(image.secondary_garments_json) if image is not None else [],
            "core_accessories": list(image.core_accessories_json) if image is not None else [],
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
            "negative_constraints": negative_constraints,
            "styling_advice": styling_advice,
            "historical_context": historical_context,
            "cultural_context": cultural_context,
            "fashion_summary": profile.fashion_summary if profile is not None else None,
            "visual_summary": profile.visual_summary if profile is not None else None,
            "image_prompt_notes": image_prompt_notes,
            "core_definition": knowledge.core_definition if knowledge is not None else None,
            "core_style_logic": list(knowledge.core_style_logic_json) if knowledge is not None else [],
            "styling_rules": list(knowledge.styling_rules_json) if knowledge is not None else [],
            "casual_adaptations": list(knowledge.casual_adaptations_json) if knowledge is not None else [],
            "statement_pieces": list(knowledge.statement_pieces_json) if knowledge is not None else [],
            "status_markers": list(knowledge.status_markers_json) if knowledge is not None else [],
            "overlap_context": list(knowledge.overlap_context_json) if knowledge is not None else [],
            "historical_notes": list(knowledge.historical_notes_json) if knowledge is not None else [],
            "negative_guidance": list(knowledge.negative_guidance_json) if knowledge is not None else [],
            "lighting_mood": list(visual.lighting_mood_json) if visual is not None else [],
            "photo_treatment": list(visual.photo_treatment_json) if visual is not None else [],
            "visual_motifs": list(visual.visual_motifs_json) if visual is not None else [],
            "platform_visual_cues": list(visual.platform_visual_cues_json) if visual is not None else [],
            "tops": list(fashion.tops_json) if fashion is not None else [],
            "bottoms": list(fashion.bottoms_json) if fashion is not None else [],
            "shoes": list(fashion.shoes_json) if fashion is not None else [],
            "hair_makeup": list(fashion.hair_makeup_json) if fashion is not None else [],
            "signature_details": list(fashion.signature_details_json) if fashion is not None else [],
            "props": list(image.props_json) if image is not None else [],
            "composition_cues": list(image.composition_cues_json) if image is not None else [],
            "related_styles": list(relation_facet.related_styles_json) if relation_facet is not None else [],
            "overlap_styles": list(relation_facet.overlap_styles_json) if relation_facet is not None else [],
            "preceded_by": list(relation_facet.preceded_by_json) if relation_facet is not None else [],
            "succeeded_by": list(relation_facet.succeeded_by_json) if relation_facet is not None else [],
            "brands": list(relation_facet.brands_json) if relation_facet is not None else [],
            "platforms": list(relation_facet.platforms_json) if relation_facet is not None else [],
            "origin_regions": list(relation_facet.origin_regions_json) if relation_facet is not None else [],
            "era": list(relation_facet.era_json) if relation_facet is not None else [],
            "presentation_short_explanation": presentation.short_explanation if presentation is not None else None,
            "presentation_one_sentence_description": (
                presentation.one_sentence_description if presentation is not None else None
            ),
            "what_makes_it_distinct": (
                list(presentation.what_makes_it_distinct_json) if presentation is not None else []
            ),
            "has_enriched_facets": any(
                facet is not None
                for facet in (
                    knowledge,
                    visual,
                    fashion,
                    image,
                    relation_facet,
                    presentation,
                )
            ),
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
            summary=summary,
            body=body,
            tags=self._unique_strings(
                [
                    style.slug,
                    style.display_name,
                    style.canonical_name,
                    *alias_values,
                    *palette,
                    *hero_garments,
                    *materials,
                    *footwear,
                    *accessories,
                    *silhouettes,
                    *occasion_fit,
                    *seasonality,
                    *mood_keywords,
                    *trait_values,
                    *metadata["statement_pieces"],
                    *metadata["brands"],
                    *metadata["platforms"],
                    *metadata["origin_regions"],
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
