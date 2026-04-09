from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.styles.contracts import (
    StylePersistencePayload,
    StylePersistenceResult,
    ValidatedStyleDocument,
)
from app.models.style import Style
from app.models.style_alias import StyleAlias
from app.models.style_ingest_change import StyleIngestChange
from app.models.style_profile import StyleProfile
from app.models.style_relation import StyleRelation
from app.models.style_source import StyleSource
from app.models.style_source_evidence import StyleSourceEvidence
from app.models.style_source_image import StyleSourceImage
from app.models.style_source_link import StyleSourceLink
from app.models.style_source_section import StyleSourceSection
from app.models.style_taxonomy_link import StyleTaxonomyLink
from app.models.style_taxonomy_node import StyleTaxonomyNode
from app.models.style_trait import StyleTrait


STYLE_CORE_FIELDS = (
    "canonical_name",
    "slug",
    "display_name",
    "status",
    "source_primary_id",
    "short_definition",
    "long_summary",
    "confidence_score",
)

PROFILE_FIELDS = (
    "essence",
    "fashion_summary",
    "visual_summary",
    "historical_context",
    "cultural_context",
    "mood_keywords_json",
    "color_palette_json",
    "materials_json",
    "silhouettes_json",
    "garments_json",
    "footwear_json",
    "accessories_json",
    "hair_makeup_json",
    "patterns_textures_json",
    "seasonality_json",
    "occasion_fit_json",
    "negative_constraints_json",
    "styling_advice_json",
    "image_prompt_notes_json",
)


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported value for hashing: {type(value)!r}")


def _hash_value(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=_json_default)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_snapshot(source: StyleSource | None) -> dict[str, Any] | None:
    if source is None:
        return None
    return {
        "source_url": source.source_url,
        "source_site": source.source_site,
        "source_title": source.source_title,
        "fetched_at": source.fetched_at,
        "last_seen_at": source.last_seen_at,
        "source_hash": source.source_hash,
        "raw_html": source.raw_html,
        "raw_text": source.raw_text,
        "raw_sections_json": source.raw_sections_json,
        "parser_version": source.parser_version,
        "normalizer_version": source.normalizer_version,
    }


def _style_snapshot(style: Style | None) -> dict[str, Any] | None:
    if style is None:
        return None
    return {field_name: getattr(style, field_name) for field_name in STYLE_CORE_FIELDS}


def _profile_snapshot(profile: StyleProfile | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    return {field_name: getattr(profile, field_name) for field_name in PROFILE_FIELDS}


def _normalize_alias_snapshot(records: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for record in records:
        normalized = {
            "alias": record.get("alias"),
            "alias_type": record.get("alias_type"),
            "language": record.get("language"),
            "is_primary_match_hint": bool(record.get("is_primary_match_hint", False)),
        }
        key = (
            normalized["alias"],
            normalized["alias_type"],
            normalized["language"],
            normalized["is_primary_match_hint"],
        )
        deduped[key] = normalized
    return tuple(sorted(deduped.values(), key=lambda item: (item["alias"] or "", item["language"] or "")))


def _normalize_trait_snapshot(records: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    normalized = [
        {
            "trait_type": record.get("trait_type"),
            "trait_value": record.get("trait_value"),
            "weight": float(record.get("weight", 1.0)),
        }
        for record in records
    ]
    return tuple(sorted(normalized, key=lambda item: (item["trait_type"] or "", item["trait_value"] or "")))


def _normalize_taxonomy_snapshot(records: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    normalized = [
        {
            "taxonomy_type": record.get("taxonomy_type"),
            "name": record.get("name"),
            "slug": record.get("slug"),
            "description": record.get("description"),
            "link_strength": float(record.get("link_strength", 1.0)),
        }
        for record in records
    ]
    return tuple(sorted(normalized, key=lambda item: (item["taxonomy_type"] or "", item["slug"] or "")))


def _normalize_relation_snapshot(records: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    normalized = [
        {
            "target_style_slug": record.get("target_style_slug"),
            "relation_type": record.get("relation_type"),
            "score": float(record.get("score", 1.0)),
            "reason": record.get("reason"),
        }
        for record in records
    ]
    return tuple(
        sorted(normalized, key=lambda item: (item["target_style_slug"] or "", item["relation_type"] or ""))
    )


def _normalize_profile_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {field_name: payload.get(field_name) for field_name in PROFILE_FIELDS}


def _slug_to_title(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-") if part) or slug


class SQLAlchemyStyleDBWriter:
    def __init__(self, session: AsyncSession, *, run_id: int | None = None) -> None:
        self.session = session
        self.run_id = run_id

    async def persist(self, payload: StylePersistencePayload) -> StylePersistenceResult:
        source = await self._get_source(
            source_site=payload.source_record["source_site"],
            source_url=payload.source_record["source_url"],
        )
        source_before = _source_snapshot(source)
        source_created = source is None

        style = await self._get_style_by_slug(payload.style_record["slug"])
        style_before = _style_snapshot(style)
        style_created = style is None
        profile_before = await self._load_profile_snapshot(style.id) if style is not None else None
        alias_before = await self._load_alias_snapshot(style.id) if style is not None else ()
        trait_before = await self._load_trait_snapshot(style.id) if style is not None else ()
        taxonomy_before = await self._load_taxonomy_snapshot(style.id) if style is not None else ()
        relation_before = await self._load_relation_snapshot(style.id) if style is not None else ()

        source = await self._upsert_source(source, payload.source_record)

        if style is not None:
            await self._delete_style_dependents(style.id)
        await self._delete_source_dependents(source.id)

        sections = await self._replace_source_sections(source.id, payload.section_records)
        await self._replace_source_links(source.id, payload.link_records)
        style = await self._upsert_style(style, source.id, payload.style_record)
        profile = await self._upsert_profile(style.id, payload.profile_record)
        await self._replace_aliases(style.id, payload.alias_records)
        await self._replace_traits(style.id, source.id, sections, payload, payload.trait_records)
        await self._replace_taxonomy_links(style.id, source.id, sections, payload, payload.taxonomy_records)
        await self._replace_relations(style.id, source.id, sections, payload, payload.relation_records)
        await self.session.flush()

        source_after = _source_snapshot(source)
        style_after = _style_snapshot(style)
        profile_after = _profile_snapshot(profile)
        alias_after = _normalize_alias_snapshot(list(payload.alias_records))
        trait_after = _normalize_trait_snapshot(list(payload.trait_records))
        taxonomy_after = _normalize_taxonomy_snapshot(list(payload.taxonomy_records))
        relation_after = _normalize_relation_snapshot(list(payload.relation_records))

        await self._log_source_changes(
            source_id=source.id,
            style_id=style.id,
            source_before=source_before,
            source_after=source_after,
            source_created=source_created,
        )
        await self._log_style_changes(
            style_id=style.id,
            style_before=style_before,
            style_after=style_after,
            style_created=style_created,
        )
        await self._log_profile_changes(
            style_id=style.id,
            profile_before=profile_before,
            profile_after=profile_after,
        )
        await self._log_collection_change(
            style_id=style.id,
            change_type="aliases_synced",
            field_name="style_aliases",
            old_value=alias_before,
            new_value=alias_after,
        )
        await self._log_collection_change(
            style_id=style.id,
            change_type="traits_synced",
            field_name="style_traits",
            old_value=trait_before,
            new_value=trait_after,
        )
        await self._log_collection_change(
            style_id=style.id,
            change_type="taxonomy_synced",
            field_name="style_taxonomy_links",
            old_value=taxonomy_before,
            new_value=taxonomy_after,
        )
        await self._log_collection_change(
            style_id=style.id,
            change_type="relations_synced",
            field_name="style_relations",
            old_value=relation_before,
            new_value=relation_after,
        )

        style_updated = not style_created and (
            style_before != style_after
            or profile_before != profile_after
            or alias_before != alias_after
            or trait_before != trait_after
            or taxonomy_before != taxonomy_after
            or relation_before != relation_after
        )

        return StylePersistenceResult(
            source_id=source.id,
            style_id=style.id,
            style_slug=style.slug,
            was_source_created=source_created,
            was_style_created=style_created,
            was_style_updated=style_updated,
        )

    async def _get_source(self, *, source_site: str, source_url: str) -> StyleSource | None:
        result = await self.session.execute(
            select(StyleSource)
            .where(StyleSource.source_site == source_site, StyleSource.source_url == source_url)
            .order_by(StyleSource.id.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_style_by_slug(self, slug: str) -> Style | None:
        result = await self.session.execute(select(Style).where(Style.slug == slug).limit(1))
        return result.scalar_one_or_none()

    async def _upsert_source(self, source: StyleSource | None, record: dict[str, Any]) -> StyleSource:
        if source is None:
            source = StyleSource(**record)
        else:
            for key, value in record.items():
                setattr(source, key, value)
        self.session.add(source)
        await self.session.flush()
        return source

    async def _delete_source_dependents(self, source_id: int) -> None:
        await self.session.execute(delete(StyleSourceEvidence).where(StyleSourceEvidence.source_page_id == source_id))
        await self.session.execute(delete(StyleSourceSection).where(StyleSourceSection.source_page_id == source_id))
        await self.session.execute(delete(StyleSourceLink).where(StyleSourceLink.source_page_id == source_id))
        await self.session.execute(delete(StyleSourceImage).where(StyleSourceImage.source_page_id == source_id))

    async def _delete_style_dependents(self, style_id: int) -> None:
        await self.session.execute(delete(StyleRelation).where(StyleRelation.source_style_id == style_id))
        await self.session.execute(delete(StyleTaxonomyLink).where(StyleTaxonomyLink.style_id == style_id))
        await self.session.execute(delete(StyleTrait).where(StyleTrait.style_id == style_id))
        await self.session.execute(delete(StyleAlias).where(StyleAlias.style_id == style_id))

    async def _replace_source_sections(
        self,
        source_id: int,
        records: tuple[dict[str, Any], ...],
    ) -> tuple[StyleSourceSection, ...]:
        section_models: list[StyleSourceSection] = []
        for record in records:
            section = StyleSourceSection(source_page_id=source_id, **record)
            self.session.add(section)
            section_models.append(section)
        await self.session.flush()
        return tuple(section_models)

    async def _replace_source_links(self, source_id: int, records: tuple[dict[str, Any], ...]) -> None:
        for record in records:
            self.session.add(StyleSourceLink(source_page_id=source_id, **record))
        await self.session.flush()

    async def _upsert_style(self, style: Style | None, source_id: int, record: dict[str, Any]) -> Style:
        payload = {
            "canonical_name": record["canonical_name"],
            "slug": record["slug"],
            "display_name": record["display_name"],
            "status": record.get("status", "active"),
            "source_primary_id": source_id,
            "short_definition": record.get("short_definition"),
            "long_summary": record.get("long_summary"),
            "confidence_score": float(record.get("confidence_score", 1.0)),
        }
        if style is None:
            style = Style(**payload)
        else:
            for key, value in payload.items():
                setattr(style, key, value)
        self.session.add(style)
        await self.session.flush()
        return style

    async def _upsert_profile(self, style_id: int, payload: dict[str, Any]) -> StyleProfile:
        result = await self.session.execute(select(StyleProfile).where(StyleProfile.style_id == style_id).limit(1))
        profile = result.scalar_one_or_none()
        normalized_payload = _normalize_profile_payload(payload)
        if profile is None:
            profile = StyleProfile(style_id=style_id, **normalized_payload)
        else:
            for key, value in normalized_payload.items():
                setattr(profile, key, value)
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def _replace_aliases(self, style_id: int, records: tuple[dict[str, Any], ...]) -> None:
        normalized_records = _normalize_alias_snapshot(list(records))
        for index, record in enumerate(normalized_records):
            self.session.add(
                StyleAlias(
                    style_id=style_id,
                    alias=record["alias"],
                    alias_type=record["alias_type"] or "exact",
                    language=record["language"],
                    is_primary_match_hint=record["is_primary_match_hint"] or index == 0,
                )
            )
        await self.session.flush()

    async def _replace_traits(
        self,
        style_id: int,
        source_id: int,
        sections: tuple[StyleSourceSection, ...],
        payload: StylePersistencePayload,
        records: tuple[dict[str, Any], ...],
    ) -> None:
        evidence_cache: dict[tuple[str, str], int] = {}
        for record in records:
            evidence_id = await self._ensure_evidence(
                evidence_cache=evidence_cache,
                source_id=source_id,
                sections=sections,
                evidence_kind=record.get("evidence_kind", "derived_summary"),
                evidence_text=record.get("evidence_text")
                or payload.style_record.get("short_definition")
                or payload.source_record["source_title"],
            )
            self.session.add(
                StyleTrait(
                    style_id=style_id,
                    trait_type=record["trait_type"],
                    trait_value=record["trait_value"],
                    weight=float(record.get("weight", 1.0)),
                    source_evidence_id=evidence_id,
                )
            )
        await self.session.flush()

    async def _replace_taxonomy_links(
        self,
        style_id: int,
        source_id: int,
        sections: tuple[StyleSourceSection, ...],
        payload: StylePersistencePayload,
        records: tuple[dict[str, Any], ...],
    ) -> None:
        evidence_cache: dict[tuple[str, str], int] = {}
        for record in records:
            node = await self._get_or_create_taxonomy_node(
                taxonomy_type=record["taxonomy_type"],
                slug=record["slug"],
                name=record["name"],
                description=record.get("description"),
            )
            evidence_id = await self._ensure_evidence(
                evidence_cache=evidence_cache,
                source_id=source_id,
                sections=sections,
                evidence_kind=record.get("evidence_kind", "derived_summary"),
                evidence_text=record.get("evidence_text")
                or payload.style_record.get("short_definition")
                or payload.source_record["source_title"],
            )
            self.session.add(
                StyleTaxonomyLink(
                    style_id=style_id,
                    taxonomy_node_id=node.id,
                    link_strength=float(record.get("link_strength", 1.0)),
                    source_evidence_id=evidence_id,
                )
            )
        await self.session.flush()

    async def _replace_relations(
        self,
        style_id: int,
        source_id: int,
        sections: tuple[StyleSourceSection, ...],
        payload: StylePersistencePayload,
        records: tuple[dict[str, Any], ...],
    ) -> None:
        evidence_cache: dict[tuple[str, str], int] = {}
        for record in records:
            target_style = await self._get_or_create_relation_target_style(record["target_style_slug"])
            if target_style.id == style_id:
                continue
            evidence_id = await self._ensure_evidence(
                evidence_cache=evidence_cache,
                source_id=source_id,
                sections=sections,
                evidence_kind=record.get("evidence_kind", "derived_summary"),
                evidence_text=record.get("evidence_text")
                or record.get("reason")
                or payload.style_record.get("short_definition")
                or payload.source_record["source_title"],
            )
            self.session.add(
                StyleRelation(
                    source_style_id=style_id,
                    target_style_id=target_style.id,
                    relation_type=record["relation_type"],
                    score=float(record.get("score", 1.0)),
                    reason=record.get("reason"),
                    source_evidence_id=evidence_id,
                )
            )
        await self.session.flush()

    async def _get_or_create_taxonomy_node(
        self,
        *,
        taxonomy_type: str,
        slug: str,
        name: str,
        description: str | None,
    ) -> StyleTaxonomyNode:
        result = await self.session.execute(
            select(StyleTaxonomyNode)
            .where(StyleTaxonomyNode.taxonomy_type == taxonomy_type, StyleTaxonomyNode.slug == slug)
            .limit(1)
        )
        node = result.scalar_one_or_none()
        if node is None:
            node = StyleTaxonomyNode(
                taxonomy_type=taxonomy_type,
                slug=slug,
                name=name,
                description=description,
            )
        else:
            node.name = name
            node.description = description
        self.session.add(node)
        await self.session.flush()
        return node

    async def _get_or_create_relation_target_style(self, slug: str) -> Style:
        style = await self._get_style_by_slug(slug)
        if style is not None:
            return style
        title = _slug_to_title(slug)
        style = Style(
            canonical_name=title,
            slug=slug,
            display_name=title,
            status="draft",
            source_primary_id=None,
            short_definition=None,
            long_summary=None,
            confidence_score=0.0,
        )
        self.session.add(style)
        await self.session.flush()
        return style

    async def _ensure_evidence(
        self,
        *,
        evidence_cache: dict[tuple[str, str], int],
        source_id: int,
        sections: tuple[StyleSourceSection, ...],
        evidence_kind: str,
        evidence_text: str,
    ) -> int:
        cache_key = (evidence_kind, evidence_text)
        cached = evidence_cache.get(cache_key)
        if cached is not None:
            return cached

        source_section_id = self._match_section_id(sections, evidence_text)
        evidence = StyleSourceEvidence(
            source_page_id=source_id,
            source_section_id=source_section_id,
            evidence_kind=evidence_kind,
            evidence_text=evidence_text,
            confidence_score=1.0,
            metadata_json={"ingestion_stage": "style_db_writer"},
        )
        self.session.add(evidence)
        await self.session.flush()
        evidence_cache[cache_key] = evidence.id
        return evidence.id

    def _match_section_id(self, sections: tuple[StyleSourceSection, ...], evidence_text: str) -> int | None:
        for section in sections:
            if evidence_text and evidence_text in section.section_text:
                return section.id
        if sections:
            return sections[0].id
        return None

    async def _load_profile_snapshot(self, style_id: int) -> dict[str, Any] | None:
        result = await self.session.execute(select(StyleProfile).where(StyleProfile.style_id == style_id).limit(1))
        return _profile_snapshot(result.scalar_one_or_none())

    async def _load_alias_snapshot(self, style_id: int) -> tuple[dict[str, Any], ...]:
        result = await self.session.execute(select(StyleAlias).where(StyleAlias.style_id == style_id))
        records = [
            {
                "alias": item.alias,
                "alias_type": item.alias_type,
                "language": item.language,
                "is_primary_match_hint": item.is_primary_match_hint,
            }
            for item in result.scalars().all()
        ]
        return _normalize_alias_snapshot(records)

    async def _load_trait_snapshot(self, style_id: int) -> tuple[dict[str, Any], ...]:
        result = await self.session.execute(select(StyleTrait).where(StyleTrait.style_id == style_id))
        records = [
            {
                "trait_type": item.trait_type,
                "trait_value": item.trait_value,
                "weight": item.weight,
            }
            for item in result.scalars().all()
        ]
        return _normalize_trait_snapshot(records)

    async def _load_taxonomy_snapshot(self, style_id: int) -> tuple[dict[str, Any], ...]:
        result = await self.session.execute(
            select(StyleTaxonomyLink, StyleTaxonomyNode)
            .join(StyleTaxonomyNode, StyleTaxonomyNode.id == StyleTaxonomyLink.taxonomy_node_id)
            .where(StyleTaxonomyLink.style_id == style_id)
        )
        records = [
            {
                "taxonomy_type": node.taxonomy_type,
                "name": node.name,
                "slug": node.slug,
                "description": node.description,
                "link_strength": link.link_strength,
            }
            for link, node in result.all()
        ]
        return _normalize_taxonomy_snapshot(records)

    async def _load_relation_snapshot(self, style_id: int) -> tuple[dict[str, Any], ...]:
        result = await self.session.execute(select(StyleRelation).where(StyleRelation.source_style_id == style_id))
        relation_rows = result.scalars().all()
        if not relation_rows:
            return ()

        target_ids = tuple({relation.target_style_id for relation in relation_rows})
        target_result = await self.session.execute(select(Style).where(Style.id.in_(target_ids)))
        target_map = {style.id: style.slug for style in target_result.scalars().all()}
        records = [
            {
                "target_style_slug": target_map.get(item.target_style_id),
                "relation_type": item.relation_type,
                "score": item.score,
                "reason": item.reason,
            }
            for item in relation_rows
        ]
        return _normalize_relation_snapshot(records)

    async def _log_source_changes(
        self,
        *,
        source_id: int,
        style_id: int,
        source_before: dict[str, Any] | None,
        source_after: dict[str, Any] | None,
        source_created: bool,
    ) -> None:
        if source_after is None:
            return
        if source_created:
            await self._create_change(
                style_id=style_id,
                change_type="source_created",
                field_name="style_sources",
                old_value=None,
                new_value=source_after,
                summary=f"Created source snapshot #{source_id}",
            )
            return
        if source_before == source_after:
            return
        await self._create_change(
            style_id=style_id,
            change_type="source_updated",
            field_name="style_sources",
            old_value=source_before,
            new_value=source_after,
            summary=f"Updated source snapshot #{source_id}",
        )

    async def _log_style_changes(
        self,
        *,
        style_id: int,
        style_before: dict[str, Any] | None,
        style_after: dict[str, Any] | None,
        style_created: bool,
    ) -> None:
        if style_after is None:
            return
        if style_created:
            await self._create_change(
                style_id=style_id,
                change_type="style_created",
                field_name="styles",
                old_value=None,
                new_value=style_after,
                summary=f"Created canonical style {style_after['slug']}",
            )
            return

        for field_name in STYLE_CORE_FIELDS:
            old_value = None if style_before is None else style_before.get(field_name)
            new_value = style_after.get(field_name)
            if old_value == new_value:
                continue
            await self._create_change(
                style_id=style_id,
                change_type="style_field_updated",
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                summary=f"Updated style field {field_name}",
            )

    async def _log_profile_changes(
        self,
        *,
        style_id: int,
        profile_before: dict[str, Any] | None,
        profile_after: dict[str, Any] | None,
    ) -> None:
        if profile_after is None:
            return
        if profile_before is None:
            await self._create_change(
                style_id=style_id,
                change_type="profile_created",
                field_name="style_profiles",
                old_value=None,
                new_value=profile_after,
                summary="Created normalized style profile",
            )
            return
        if profile_before == profile_after:
            return
        await self._create_change(
            style_id=style_id,
            change_type="profile_updated",
            field_name="style_profiles",
            old_value=profile_before,
            new_value=profile_after,
            summary="Updated normalized style profile",
        )

    async def _log_collection_change(
        self,
        *,
        style_id: int,
        change_type: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        if old_value == new_value:
            return
        await self._create_change(
            style_id=style_id,
            change_type=change_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            summary=f"Synchronized collection {field_name}",
        )

    async def _create_change(
        self,
        *,
        style_id: int | None,
        change_type: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        summary: str,
    ) -> None:
        if self.run_id is None:
            return
        change = StyleIngestChange(
            run_id=self.run_id,
            style_id=style_id,
            change_type=change_type,
            field_name=field_name,
            old_value_hash=None if old_value is None else _hash_value(old_value),
            new_value_hash=None if new_value is None else _hash_value(new_value),
            change_summary=summary,
        )
        self.session.add(change)
        await self.session.flush()


def build_style_persistence_payload(document: ValidatedStyleDocument) -> StylePersistencePayload:
    enriched = document.enriched
    normalized = enriched.normalized

    source_record = {
        "source_url": normalized.source_url,
        "source_site": normalized.source_site,
        "source_title": normalized.source_title,
        "fetched_at": normalized.fetched_at,
        "last_seen_at": normalized.fetched_at,
        "source_hash": normalized.source_hash,
        "raw_html": normalized.raw_html,
        "raw_text": normalized.raw_text,
        "raw_sections_json": [
            {
                "section_order": section.section_order,
                "section_title": section.section_title,
                "section_level": section.section_level,
                "section_text": section.section_text,
                "section_hash": section.section_hash,
            }
            for section in normalized.sections
        ],
        "parser_version": normalized.parser_version,
        "normalizer_version": normalized.normalizer_version,
    }

    section_records = tuple(
        {
            "section_order": section.section_order,
            "section_title": section.section_title,
            "section_level": section.section_level,
            "section_text": section.section_text,
            "section_hash": section.section_hash,
        }
        for section in normalized.sections
    )
    link_records = tuple(
        {
            "anchor_text": link.anchor_text,
            "target_title": link.target_title,
            "target_url": link.target_url,
            "link_type": link.link_type,
        }
        for link in normalized.links
    )
    style_record = {
        "canonical_name": enriched.canonical_name,
        "slug": enriched.slug,
        "display_name": enriched.display_name,
        "short_definition": enriched.short_definition,
        "long_summary": enriched.long_summary,
        "confidence_score": enriched.confidence_score,
    }
    alias_records = tuple(
        {
            "alias": alias,
            "alias_type": "exact",
            "language": None,
            "is_primary_match_hint": False,
        }
        for alias in enriched.alias_candidates
    )
    profile_record = dict(enriched.profile_payload)
    trait_records = tuple(
        {
            "trait_type": trait.trait_type,
            "trait_value": trait.trait_value,
            "weight": trait.weight,
            "evidence_kind": trait.evidence_kind,
            "evidence_text": trait.evidence_text,
        }
        for trait in enriched.trait_seeds
    )
    taxonomy_records = tuple(
        {
            "taxonomy_type": taxonomy.taxonomy_type,
            "name": taxonomy.name,
            "slug": taxonomy.slug,
            "description": taxonomy.description,
            "link_strength": taxonomy.link_strength,
            "evidence_kind": taxonomy.evidence_kind,
            "evidence_text": taxonomy.evidence_text,
        }
        for taxonomy in enriched.taxonomy_link_seeds
    )
    relation_records = tuple(
        {
            "target_style_slug": relation.target_style_slug,
            "relation_type": relation.relation_type,
            "score": relation.score,
            "reason": relation.reason,
            "evidence_kind": relation.evidence_kind,
            "evidence_text": relation.evidence_text,
        }
        for relation in enriched.relation_seeds
    )

    return StylePersistencePayload(
        source_record=source_record,
        section_records=section_records,
        link_records=link_records,
        style_record=style_record,
        alias_records=alias_records,
        profile_record=profile_record,
        trait_records=trait_records,
        taxonomy_records=taxonomy_records,
        relation_records=relation_records,
    )
