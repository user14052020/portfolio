from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain.knowledge.entities import (
    KnowledgeCard,
    KnowledgeChunk,
    KnowledgeDocument,
    StyleKnowledgeProjectionResult,
)
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
class StyleFacetProjectionSource:
    style: Style
    profile: StyleProfile | None
    source: StyleSource | None
    aliases: list[StyleAlias]
    traits: list[StyleTrait]
    relations: list[StyleRelation]
    knowledge_facet: StyleKnowledgeFacet | None = None
    visual_facet: StyleVisualFacet | None = None
    fashion_facet: StyleFashionItemFacet | None = None
    image_facet: StyleImageFacet | None = None
    relation_facet: StyleRelationFacet | None = None
    presentation_facet: StylePresentationFacet | None = None


class DefaultStyleFacetKnowledgeProjector:
    def __init__(
        self,
        *,
        provider_code: str = "style_ingestion",
        provider_priority: int = 10,
        projection_version: str = "style-facet-projector.v1",
    ) -> None:
        self._provider_code = provider_code
        self._provider_priority = provider_priority
        self._projection_version = projection_version

    async def project(self, *, style_id: int) -> StyleKnowledgeProjectionResult:
        raise NotImplementedError("DefaultStyleFacetKnowledgeProjector requires a hydrated source bundle.")

    def project_from_source(self, *, source: StyleFacetProjectionSource) -> StyleKnowledgeProjectionResult:
        compatibility_card, metadata, tags, summary, body = self._build_compatibility_card(source=source)
        document = self._build_document(source=source, summary=summary, body=body, metadata=metadata)
        chunks, cards = self._build_chunks_and_cards(
            source=source,
            document=document,
            base_metadata=metadata,
            compatibility_card=compatibility_card,
            tags=tags,
        )
        return StyleKnowledgeProjectionResult(
            provider_code=self._provider_code,
            style_id=source.style.id,
            style_slug=source.style.slug,
            style_name=source.style.display_name,
            projection_version=self._projection_version,
            parser_version=source.source.parser_version if source.source is not None else None,
            normalizer_version=source.source.normalizer_version if source.source is not None else None,
            facet_version=self._facet_version(source),
            documents=[document],
            chunks=chunks,
            cards=cards,
        )

    def _build_document(
        self,
        *,
        source: StyleFacetProjectionSource,
        summary: str,
        body: str | None,
        metadata: dict[str, Any],
    ) -> KnowledgeDocument:
        text_parts = [
            summary,
            body or "",
            metadata.get("historical_context") or "",
            metadata.get("cultural_context") or "",
        ]
        clean_text = "\n\n".join(part.strip() for part in text_parts if isinstance(part, str) and part.strip())
        return KnowledgeDocument(
            id=f"knowledge_document:{source.style.slug}:{self._facet_version(source) or 'legacy'}",
            provider_code=self._provider_code,
            title=source.style.display_name,
            author=source.source.source_site if source.source is not None else None,
            source_ref=source.source.source_url if source.source is not None else None,
            raw_text=clean_text,
            clean_text=clean_text,
            version=self._document_version(source),
            metadata={
                "style_numeric_id": source.style.id,
                "style_slug": source.style.slug,
                "projection_version": self._projection_version,
                "facet_version": self._facet_version(source),
                "parser_version": source.source.parser_version if source.source is not None else None,
                "normalizer_version": source.source.normalizer_version if source.source is not None else None,
                "knowledge_types": list(self._projectable_knowledge_types(source)),
                **metadata,
            },
        )

    def _build_chunks_and_cards(
        self,
        *,
        source: StyleFacetProjectionSource,
        document: KnowledgeDocument,
        base_metadata: dict[str, Any],
        compatibility_card: KnowledgeCard,
        tags: list[str],
    ) -> tuple[list[KnowledgeChunk], list[KnowledgeCard]]:
        chunk_specs = self._chunk_specs(source=source, base_metadata=base_metadata)
        chunks: list[KnowledgeChunk] = []
        cards: list[KnowledgeCard] = [compatibility_card]
        for index, spec in enumerate(chunk_specs, start=1):
            chunks.append(
                KnowledgeChunk(
                    id=f"knowledge_chunk:{source.style.slug}:{spec['knowledge_type'].value}:{index}",
                    document_id=document.id,
                    chunk_index=index,
                    knowledge_type=spec["knowledge_type"],
                    chunk_text=spec["chunk_text"],
                    summary=spec["summary"],
                    tags=spec["tags"],
                    metadata=spec["metadata"],
                )
            )
            cards.append(
                KnowledgeCard(
                    id=f"{spec['knowledge_type'].value}:{source.style.slug}",
                    knowledge_type=spec["knowledge_type"],
                    provider_code=self._provider_code,
                    provider_priority=self._provider_priority,
                    title=spec["title"],
                    summary=spec["summary"],
                    body=spec["chunk_text"],
                    tone_role=spec.get("tone_role"),
                    tags=self._unique_strings([*tags, *spec["tags"]]),
                    style_id=source.style.slug,
                    style_family=spec["metadata"].get("style_family"),
                    era_code=spec["metadata"].get("era_code"),
                    source_ref=document.source_ref,
                    document_ref=document.id,
                    chunk_ref=chunks[-1].id,
                    confidence=compatibility_card.confidence,
                    freshness=compatibility_card.freshness,
                    metadata=spec["metadata"],
                )
            )
        return chunks, cards

    def _chunk_specs(
        self,
        *,
        source: StyleFacetProjectionSource,
        base_metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        style_family = (base_metadata.get("overlap_styles") or [None])[0]
        era_code = (base_metadata.get("era") or [None])[0]
        common = {
            "style_numeric_id": source.style.id,
            "style_slug": source.style.slug,
            "style_name": source.style.display_name,
            "style_family": style_family,
            "era_code": era_code,
            "projection_version": self._projection_version,
            "facet_version": self._facet_version(source),
            "parser_version": source.source.parser_version if source.source is not None else None,
        }
        specs: list[dict[str, Any]] = []
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_DESCRIPTION,
            title=f"{source.style.display_name} Description",
            summary=base_metadata.get("core_definition") or source.style.short_definition or source.style.display_name,
            values=[
                base_metadata.get("core_definition"),
                base_metadata.get("presentation_short_explanation"),
                base_metadata.get("presentation_one_sentence_description"),
                base_metadata.get("fashion_summary"),
                base_metadata.get("visual_summary"),
            ],
            tags=[source.style.slug, source.style.display_name],
            metadata={**common, "card_role": "style_description"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_STYLING_RULES,
            title=f"{source.style.display_name} Styling Rules",
            summary=self._summary_from_values(base_metadata.get("styling_rules"), fallback="Styling rules"),
            values=[base_metadata.get("core_style_logic"), base_metadata.get("styling_rules")],
            tags=base_metadata.get("hero_garments") or [],
            metadata={**common, "card_role": "style_styling_rules"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_CASUAL_ADAPTATIONS,
            title=f"{source.style.display_name} Casual Adaptations",
            summary=self._summary_from_values(base_metadata.get("casual_adaptations"), fallback="Casual adaptations"),
            values=[base_metadata.get("casual_adaptations")],
            tags=base_metadata.get("garments") or [],
            metadata={**common, "card_role": "style_casual_adaptations"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_VISUAL_LANGUAGE,
            title=f"{source.style.display_name} Visual Language",
            summary=self._summary_from_values(base_metadata.get("visual_motifs"), fallback="Visual language"),
            values=[
                base_metadata.get("palette"),
                base_metadata.get("lighting_mood"),
                base_metadata.get("photo_treatment"),
                base_metadata.get("visual_motifs"),
                base_metadata.get("platform_visual_cues"),
            ],
            tags=(base_metadata.get("palette") or []) + (base_metadata.get("visual_motifs") or []),
            metadata={**common, "card_role": "style_visual_language"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_IMAGE_COMPOSITION,
            title=f"{source.style.display_name} Image Composition",
            summary=self._summary_from_values(base_metadata.get("composition_cues"), fallback="Image composition"),
            values=[
                base_metadata.get("hero_garments"),
                base_metadata.get("secondary_garments"),
                base_metadata.get("composition_cues"),
            ],
            tags=(base_metadata.get("hero_garments") or []) + (base_metadata.get("props") or []),
            metadata={**common, "card_role": "style_image_composition"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_PROPS,
            title=f"{source.style.display_name} Props",
            summary=self._summary_from_values(base_metadata.get("props"), fallback="Props and supporting accessories"),
            values=[base_metadata.get("props"), base_metadata.get("core_accessories"), base_metadata.get("accessories")],
            tags=(base_metadata.get("props") or []) + (base_metadata.get("accessories") or []),
            metadata={**common, "card_role": "style_props"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_RELATION_CONTEXT,
            title=f"{source.style.display_name} Relation Context",
            summary=self._summary_from_values(base_metadata.get("related_styles"), fallback="Relation context"),
            values=[
                base_metadata.get("related_styles"),
                base_metadata.get("overlap_styles"),
                base_metadata.get("preceded_by"),
                base_metadata.get("succeeded_by"),
                base_metadata.get("origin_regions"),
                base_metadata.get("era"),
                base_metadata.get("historical_notes"),
            ],
            tags=(base_metadata.get("related_styles") or []) + (base_metadata.get("origin_regions") or []),
            metadata={**common, "card_role": "style_relation_context"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_BRANDS_PLATFORMS,
            title=f"{source.style.display_name} Brands and Platforms",
            summary=self._summary_from_values(base_metadata.get("brands"), fallback="Brands and platforms"),
            values=[base_metadata.get("brands"), base_metadata.get("platforms")],
            tags=(base_metadata.get("brands") or []) + (base_metadata.get("platforms") or []),
            metadata={**common, "card_role": "style_brands_platforms"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_PALETTE_LOGIC,
            title=f"{source.style.display_name} Palette Logic",
            summary=self._summary_from_values(base_metadata.get("palette"), fallback="Palette logic"),
            values=[base_metadata.get("palette"), base_metadata.get("patterns_textures")],
            tags=base_metadata.get("palette") or [],
            metadata={**common, "card_role": "style_palette_logic"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_PHOTO_TREATMENT,
            title=f"{source.style.display_name} Photo Treatment",
            summary=self._summary_from_values(base_metadata.get("photo_treatment"), fallback="Photo treatment"),
            values=[base_metadata.get("lighting_mood"), base_metadata.get("photo_treatment")],
            tags=(base_metadata.get("lighting_mood") or []) + (base_metadata.get("photo_treatment") or []),
            metadata={**common, "card_role": "style_photo_treatment"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_SIGNATURE_DETAILS,
            title=f"{source.style.display_name} Signature Details",
            summary=self._summary_from_values(base_metadata.get("signature_details"), fallback="Signature details"),
            values=[base_metadata.get("signature_details"), base_metadata.get("statement_pieces")],
            tags=(base_metadata.get("signature_details") or []) + (base_metadata.get("statement_pieces") or []),
            metadata={**common, "card_role": "style_signature_details"},
        )
        self._append_spec(
            specs,
            knowledge_type=KnowledgeType.STYLE_NEGATIVE_GUIDANCE,
            title=f"{source.style.display_name} Negative Guidance",
            summary=self._summary_from_values(base_metadata.get("negative_guidance"), fallback="Negative guidance"),
            values=[base_metadata.get("negative_guidance"), base_metadata.get("negative_constraints")],
            tags=base_metadata.get("negative_constraints") or [],
            metadata={**common, "card_role": "style_negative_guidance"},
        )
        return specs

    def _append_spec(
        self,
        specs: list[dict[str, Any]],
        *,
        knowledge_type: KnowledgeType,
        title: str,
        summary: str,
        values: list[Any],
        tags: list[str],
        metadata: dict[str, Any],
    ) -> None:
        chunk_text = self._join_text_segments(*values)
        if not chunk_text:
            return
        specs.append(
            {
                "knowledge_type": knowledge_type,
                "title": title,
                "summary": summary,
                "chunk_text": chunk_text,
                "tags": self._unique_strings(tags),
                "metadata": metadata,
            }
        )

    def _build_compatibility_card(
        self,
        *,
        source: StyleFacetProjectionSource,
    ) -> tuple[KnowledgeCard, dict[str, Any], list[str], str, str | None]:
        profile = source.profile
        style_source = source.source
        knowledge = source.knowledge_facet
        visual = source.visual_facet
        fashion = source.fashion_facet
        image = source.image_facet
        relation_facet = source.relation_facet
        presentation = source.presentation_facet

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
        alias_values = [item.alias for item in source.aliases]
        trait_values = [item.trait_value for item in source.traits]
        summary = self._first_non_empty_text(
            presentation.short_explanation if presentation is not None else None,
            presentation.one_sentence_description if presentation is not None else None,
            knowledge.core_definition if knowledge is not None else None,
            source.style.short_definition,
            profile.fashion_summary if profile is not None else None,
            profile.visual_summary if profile is not None else None,
            source.style.display_name,
        )
        body = self._first_non_empty_text(
            self._join_text_segments(
                list(presentation.what_makes_it_distinct_json) if presentation is not None else [],
                list(knowledge.core_style_logic_json) if knowledge is not None else [],
                list(knowledge.styling_rules_json) if knowledge is not None else [],
                list(knowledge.historical_notes_json) if knowledge is not None else [],
                list(visual.visual_motifs_json) if visual is not None else [],
            ),
            source.style.long_summary,
            profile.visual_summary if profile is not None else None,
        ) or None
        metadata: dict[str, Any] = {
            "style_numeric_id": source.style.id,
            "style_slug": source.style.slug,
            "style_name": source.style.display_name,
            "canonical_name": source.style.canonical_name,
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
                for relation in source.relations[:6]
            ],
            "trait_map": self._trait_map(source.traits),
            "projection_version": self._projection_version,
            "facet_version": self._facet_version(source),
            "parser_version": style_source.parser_version if style_source is not None else None,
            "normalizer_version": style_source.normalizer_version if style_source is not None else None,
        }
        tags = self._unique_strings(
            [
                source.style.slug,
                source.style.display_name,
                source.style.canonical_name,
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
        )
        card = KnowledgeCard(
            id=f"style_catalog:{source.style.slug}",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            provider_code=self._provider_code,
            provider_priority=self._provider_priority,
            title=source.style.display_name,
            summary=summary,
            body=body,
            tone_role="runtime_compatibility",
            tags=tags,
            style_id=source.style.slug,
            style_family=(metadata["overlap_styles"][0] if metadata["overlap_styles"] else None),
            era_code=(metadata["era"][0] if metadata["era"] else None),
            source_ref=style_source.source_url if style_source is not None else None,
            confidence=max(source.style.confidence_score, 0.1),
            freshness=self._freshness(source.style.first_ingested_at, style_source.last_seen_at if style_source else None),
            metadata=metadata,
        )
        return card, metadata, tags, summary, body

    def _facet_version(self, source: StyleFacetProjectionSource) -> str | None:
        for facet in (
            source.knowledge_facet,
            source.visual_facet,
            source.image_facet,
            source.relation_facet,
            source.presentation_facet,
            source.fashion_facet,
        ):
            if facet is not None and facet.facet_version:
                return facet.facet_version
        return None

    def _document_version(self, source: StyleFacetProjectionSource) -> str:
        parts = [
            self._projection_version,
            self._facet_version(source) or "legacy",
            source.source.parser_version if source.source is not None else "no-parser",
            source.source.normalizer_version if source.source is not None else "no-normalizer",
        ]
        return "|".join(parts)

    def _projectable_knowledge_types(self, source: StyleFacetProjectionSource) -> list[str]:
        result = [KnowledgeType.STYLE_CATALOG.value]
        probe_map = {
            KnowledgeType.STYLE_DESCRIPTION: [source.style.short_definition, source.knowledge_facet, source.presentation_facet],
            KnowledgeType.STYLE_STYLING_RULES: [source.knowledge_facet],
            KnowledgeType.STYLE_CASUAL_ADAPTATIONS: [source.knowledge_facet],
            KnowledgeType.STYLE_VISUAL_LANGUAGE: [source.visual_facet],
            KnowledgeType.STYLE_IMAGE_COMPOSITION: [source.image_facet],
            KnowledgeType.STYLE_PROPS: [source.image_facet, source.fashion_facet],
            KnowledgeType.STYLE_RELATION_CONTEXT: [source.relation_facet],
            KnowledgeType.STYLE_BRANDS_PLATFORMS: [source.relation_facet],
            KnowledgeType.STYLE_PALETTE_LOGIC: [source.visual_facet, source.profile],
            KnowledgeType.STYLE_PHOTO_TREATMENT: [source.visual_facet, source.image_facet],
            KnowledgeType.STYLE_SIGNATURE_DETAILS: [source.fashion_facet, source.knowledge_facet],
            KnowledgeType.STYLE_NEGATIVE_GUIDANCE: [source.image_facet, source.knowledge_facet, source.profile],
        }
        for knowledge_type, probes in probe_map.items():
            if any(probe is not None for probe in probes):
                result.append(knowledge_type.value)
        return result

    def _trait_map(self, traits: list[StyleTrait]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for trait in traits:
            grouped.setdefault(trait.trait_type, []).append(trait.trait_value)
        return grouped

    def _freshness(self, default_dt: datetime, source_dt: datetime | None) -> str:
        current = source_dt or default_dt
        return current.date().isoformat()

    def _summary_from_values(self, value: Any, *, fallback: str) -> str:
        values = self._merge_unique_strings(value)
        if values:
            return values[0]
        return fallback

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
        return "; ".join(parts[:8])
