from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.styles.contracts import StyleChatGptEnrichmentService, StyleEnrichmentResult
from app.ingestion.styles.style_chatgpt_payloads import StyleEnrichmentPayload
from app.ingestion.styles.style_enrichment_observability import (
    build_style_enrichment_run_event_payload,
    build_style_enrichment_run_metric_payload,
)
from app.ingestion.styles.style_chatgpt_prompt_builder import (
    STYLE_ENRICHMENT_FACET_VERSION,
    STYLE_ENRICHMENT_PROMPT_VERSION,
    STYLE_ENRICHMENT_SCHEMA_VERSION,
    build_style_enrichment_system_prompt,
    build_style_enrichment_user_prompt,
)
from app.integrations.openai_chatgpt import (
    ChatGptStructuredCompletion,
    OpenAIChatGptClient,
    OpenAIChatGptClientError,
    OpenAIChatGptResponseError,
)
from app.models import (
    Style,
    StyleFashionItemFacet,
    StyleImageFacet,
    StyleKnowledgeFacet,
    StyleLlmEnrichment,
    StylePresentationFacet,
    StyleProfile,
    StyleRelationFacet,
    StyleSource,
    StyleSourceEvidence,
    StyleSourcePage,
    StyleSourcePageVersion,
    StyleSourceSection,
    StyleVisualFacet,
)


class StyleEnrichmentError(RuntimeError):
    pass


class StyleEnrichmentSourceLoadError(StyleEnrichmentError):
    pass


class StyleEnrichmentValidationError(StyleEnrichmentError):
    pass


class StyleEnrichmentWriteError(StyleEnrichmentError):
    pass


@dataclass(frozen=True)
class _LoadedStyleEnrichmentSource:
    style_id: int
    style_slug: str
    style_name: str
    source_title: str | None
    source_url: str | None
    source_page_id: int | None
    cleaned_source_text: str
    evidence_items: list[str]


class DefaultStyleChatGptEnrichmentService(StyleChatGptEnrichmentService):
    MAX_VALIDATION_ATTEMPTS = 3
    MAX_SOURCE_TEXT_CHARS = 18000
    MAX_EVIDENCE_ITEMS = 8

    def __init__(
        self,
        session: AsyncSession,
        *,
        client: OpenAIChatGptClient | None = None,
        write_enabled: bool = True,
        progress_reporter: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.session = session
        self.client = client or OpenAIChatGptClient()
        self.write_enabled = write_enabled
        self.progress_reporter = progress_reporter

    async def enrich_style(self, style_id: int) -> StyleEnrichmentResult:
        try:
            loaded = await self._load_source_material(style_id=style_id)
        except StyleEnrichmentSourceLoadError as exc:
            self._emit_run_finished(
                style_id=style_id,
                source_page_id=None,
                provider="openai",
                model_name=self.client.model,
                status="failed_source_load",
                attempts=0,
                did_write=False,
                error_class=exc.__class__.__name__,
                error_message=str(exc),
            )
            raise

        self._emit_run_started(
            style_id=loaded.style_id,
            source_page_id=loaded.source_page_id,
            provider="openai",
            model_name=self.client.model,
        )

        system_prompt = build_style_enrichment_system_prompt()
        user_prompt = build_style_enrichment_user_prompt(
            style_id=loaded.style_id,
            style_slug=loaded.style_slug,
            style_name=loaded.style_name,
            source_title=loaded.source_title,
            source_url=loaded.source_url,
            source_payload=loaded.cleaned_source_text,
            evidence_items=loaded.evidence_items,
        )

        completion: ChatGptStructuredCompletion | None = None
        validation_errors: list[str] = []
        validated_payload: StyleEnrichmentPayload | None = None

        for attempt in range(1, self.MAX_VALIDATION_ATTEMPTS + 1):
            try:
                completion = await self.client.complete_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
                validated_payload = StyleEnrichmentPayload.model_validate(completion.payload)
                break
            except (OpenAIChatGptResponseError, ValidationError) as exc:
                validation_errors.append(str(exc))
                if attempt >= self.MAX_VALIDATION_ATTEMPTS:
                    if self.write_enabled:
                        await self._write_enrichment_log(
                            style_id=loaded.style_id,
                            source_page_id=loaded.source_page_id,
                            provider="openai",
                            model_name=completion.provider if completion is not None else self.client.model,
                            status="failed_validation",
                            raw_response_json=self._build_failure_payload(completion=completion),
                            error_message=str(exc),
                        )
                    self._emit_run_finished(
                        style_id=loaded.style_id,
                        source_page_id=loaded.source_page_id,
                        provider="openai",
                        model_name=completion.provider if completion is not None else self.client.model,
                        status="failed_validation",
                        attempts=attempt,
                        did_write=False,
                        error_class=exc.__class__.__name__,
                        error_message=str(exc),
                    )
                    raise StyleEnrichmentValidationError(str(exc)) from exc
            except OpenAIChatGptClientError as exc:
                if self.write_enabled:
                    await self._write_enrichment_log(
                        style_id=loaded.style_id,
                        source_page_id=loaded.source_page_id,
                        provider="openai",
                        model_name=self.client.model,
                        status="failed_transport",
                        raw_response_json=None,
                        error_message=str(exc),
                    )
                self._emit_run_finished(
                    style_id=loaded.style_id,
                    source_page_id=loaded.source_page_id,
                    provider="openai",
                    model_name=self.client.model,
                    status="failed_transport",
                    attempts=attempt,
                    did_write=False,
                    error_class=exc.__class__.__name__,
                    error_message=str(exc),
                )
                raise StyleEnrichmentError(str(exc)) from exc

        if validated_payload is None or completion is None:
            raise StyleEnrichmentValidationError("Style enrichment payload could not be validated")

        normalized_payload = validated_payload.model_dump(mode="json")

        if self.write_enabled:
            try:
                async with self.session.begin_nested():
                    await self._upsert_facet_rows(style_id=loaded.style_id, payload=normalized_payload)
                    await self._write_enrichment_log(
                        style_id=loaded.style_id,
                        source_page_id=loaded.source_page_id,
                        provider="openai",
                        model_name=completion.provider,
                        status="succeeded",
                        raw_response_json={
                            "raw_content": completion.raw_content,
                            "payload": normalized_payload,
                        },
                        error_message=None,
                    )
            except Exception as exc:  # noqa: BLE001
                await self._write_enrichment_log(
                    style_id=loaded.style_id,
                    source_page_id=loaded.source_page_id,
                    provider="openai",
                    model_name=completion.provider,
                    status="failed_write",
                    raw_response_json={
                        "raw_content": completion.raw_content,
                        "payload": normalized_payload,
                    },
                    error_message=str(exc),
                )
                self._emit_run_finished(
                    style_id=loaded.style_id,
                    source_page_id=loaded.source_page_id,
                    provider="openai",
                    model_name=completion.provider,
                    status="failed_write",
                    attempts=max(1, len(validation_errors) + 1),
                    did_write=False,
                    error_class=exc.__class__.__name__,
                    error_message=str(exc),
                )
                raise StyleEnrichmentWriteError(str(exc)) from exc

        result = StyleEnrichmentResult(
            style_id=loaded.style_id,
            style_slug=loaded.style_slug,
            source_page_id=loaded.source_page_id,
            provider="openai",
            model_name=completion.provider,
            prompt_version=STYLE_ENRICHMENT_PROMPT_VERSION,
            schema_version=STYLE_ENRICHMENT_SCHEMA_VERSION,
            status="succeeded" if self.write_enabled else "dry_run_succeeded",
            attempts=max(1, len(validation_errors) + 1),
            did_write=self.write_enabled,
            validation_errors=tuple(validation_errors),
            error_message=None,
        )
        self._emit_run_finished(
            style_id=result.style_id,
            source_page_id=result.source_page_id,
            provider=result.provider,
            model_name=result.model_name,
            status=result.status,
            attempts=result.attempts,
            did_write=result.did_write,
            error_class=None,
            error_message=None,
        )
        return result

    async def _load_source_material(self, *, style_id: int) -> _LoadedStyleEnrichmentSource:
        statement: Select[Any] = (
            select(Style, StyleSource, StyleProfile)
            .outerjoin(StyleSource, Style.source_primary_id == StyleSource.id)
            .outerjoin(StyleProfile, StyleProfile.style_id == Style.id)
            .where(Style.id == style_id)
            .limit(1)
        )
        result = await self.session.execute(statement)
        row = result.one_or_none()
        if row is None:
            raise StyleEnrichmentSourceLoadError(f"Style {style_id} was not found")

        style, source, profile = row
        if source is None:
            raise StyleEnrichmentSourceLoadError(f"Style {style_id} does not have a stored source row")

        source_page = await self._find_source_page(source=source)
        page_version = await self._find_latest_page_version(source_page_id=source_page.id) if source_page else None
        sections = await self._load_sections(source_id=source.id)
        evidences = await self._load_evidences(source_id=source.id)
        cleaned_source_text = self._build_cleaned_source_text(
            source=source,
            source_page=source_page,
            page_version=page_version,
            sections=sections,
        )
        if not cleaned_source_text:
            fallback_summary = None
            if profile is not None:
                fallback_summary = profile.fashion_summary or profile.visual_summary or profile.essence
            cleaned_source_text = (fallback_summary or source.raw_text or "").strip()

        if not cleaned_source_text:
            raise StyleEnrichmentSourceLoadError(f"Style {style_id} does not have usable stored source text")

        return _LoadedStyleEnrichmentSource(
            style_id=style.id,
            style_slug=style.slug,
            style_name=style.display_name,
            source_title=source.source_title,
            source_url=source.source_url,
            source_page_id=source_page.id if source_page is not None else None,
            cleaned_source_text=cleaned_source_text,
            evidence_items=[self._normalize_inline_text(item.evidence_text) for item in evidences if item.evidence_text.strip()],
        )

    async def _find_source_page(self, *, source: StyleSource) -> StyleSourcePage | None:
        by_url_result = await self.session.execute(
            select(StyleSourcePage)
            .where(StyleSourcePage.page_url == source.source_url)
            .order_by(StyleSourcePage.id.desc())
            .limit(1)
        )
        source_page = by_url_result.scalar_one_or_none()
        if source_page is not None:
            return source_page

        if source.remote_page_id is None:
            return None

        by_remote_id_result = await self.session.execute(
            select(StyleSourcePage)
            .where(
                StyleSourcePage.source_name == source.source_site,
                StyleSourcePage.remote_page_id == source.remote_page_id,
            )
            .order_by(StyleSourcePage.id.desc())
            .limit(1)
        )
        return by_remote_id_result.scalar_one_or_none()

    async def _find_latest_page_version(self, *, source_page_id: int) -> StyleSourcePageVersion | None:
        result = await self.session.execute(
            select(StyleSourcePageVersion)
            .where(StyleSourcePageVersion.source_page_id == source_page_id)
            .order_by(StyleSourcePageVersion.fetched_at.desc(), StyleSourcePageVersion.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _load_sections(self, *, source_id: int) -> list[StyleSourceSection]:
        result = await self.session.execute(
            select(StyleSourceSection)
            .where(StyleSourceSection.source_page_id == source_id)
            .order_by(StyleSourceSection.section_order.asc(), StyleSourceSection.id.asc())
        )
        return list(result.scalars().all())

    async def _load_evidences(self, *, source_id: int) -> list[StyleSourceEvidence]:
        result = await self.session.execute(
            select(StyleSourceEvidence)
            .where(StyleSourceEvidence.source_page_id == source_id)
            .order_by(StyleSourceEvidence.confidence_score.desc(), StyleSourceEvidence.id.asc())
            .limit(self.MAX_EVIDENCE_ITEMS)
        )
        return list(result.scalars().all())

    def _build_cleaned_source_text(
        self,
        *,
        source: StyleSource,
        source_page: StyleSourcePage | None,
        page_version: StyleSourcePageVersion | None,
        sections: list[StyleSourceSection],
    ) -> str:
        blocks: list[str] = []

        if page_version is not None and page_version.raw_sections_json:
            for item in page_version.raw_sections_json:
                if not isinstance(item, dict):
                    continue
                block = self._format_section_block(item.get("title"), item.get("text"))
                if block:
                    blocks.append(block)

        if not blocks and sections:
            for section in sections:
                block = self._format_section_block(section.section_title, section.section_text)
                if block:
                    blocks.append(block)

        if not blocks and source.raw_sections_json:
            for item in source.raw_sections_json:
                if not isinstance(item, dict):
                    continue
                block = self._format_section_block(item.get("title"), item.get("text"))
                if block:
                    blocks.append(block)

        if not blocks:
            block = self._sanitize_block_text(source.raw_text)
            if block:
                heading = source_page.source_title if source_page is not None else source.source_title
                blocks.append(self._format_section_block(heading, block) or block)

        deduped_blocks: list[str] = []
        seen: set[str] = set()
        for block in blocks:
            cleaned = block.strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped_blocks.append(cleaned)

        result = "\n\n".join(deduped_blocks).strip()
        if len(result) > self.MAX_SOURCE_TEXT_CHARS:
            return result[: self.MAX_SOURCE_TEXT_CHARS].rstrip()
        return result

    def _format_section_block(self, title: Any, text: Any) -> str | None:
        cleaned_text = self._sanitize_block_text(text)
        if not cleaned_text:
            return None
        cleaned_title = self._normalize_inline_text(title)
        if cleaned_title:
            return f"## {cleaned_title}\n{cleaned_text}"
        return cleaned_text

    def _sanitize_block_text(self, value: Any) -> str:
        if value is None:
            return ""
        lines = [line.strip() for line in str(value).splitlines()]
        kept_lines: list[str] = []
        seen: set[str] = set()
        for line in lines:
            if not line:
                continue
            lowered = line.lower()
            if lowered in seen:
                continue
            if lowered in {
                "references",
                "external links",
                "navigation",
                "comments",
                "categories",
                "gallery",
                "see also",
            }:
                continue
            if lowered.startswith("category:") or lowered.startswith("template:"):
                continue
            seen.add(lowered)
            kept_lines.append(self._normalize_inline_text(line))
        return "\n".join(line for line in kept_lines if line)

    def _normalize_inline_text(self, value: Any) -> str:
        return " ".join(str(value or "").split()).strip()

    async def _upsert_facet_rows(self, *, style_id: int, payload: dict[str, Any]) -> None:
        knowledge = payload["knowledge"]
        visual = payload["visual_language"]
        fashion_items = payload["fashion_items"]
        image_prompt = payload["image_prompt_atoms"]
        relations = payload["relations"]
        presentation = payload["presentation"]

        await self._upsert_singleton_facet(
            StyleKnowledgeFacet,
            style_id=style_id,
            payload={
                "facet_version": STYLE_ENRICHMENT_FACET_VERSION,
                "core_definition": knowledge["core_definition"],
                "core_style_logic_json": knowledge["core_style_logic"],
                "styling_rules_json": knowledge["styling_rules"],
                "casual_adaptations_json": knowledge["casual_adaptations"],
                "statement_pieces_json": knowledge["statement_pieces"],
                "status_markers_json": knowledge["status_markers"],
                "overlap_context_json": knowledge["overlap_context"],
                "historical_notes_json": knowledge["historical_notes"],
                "negative_guidance_json": knowledge["negative_guidance"],
            },
        )
        await self._upsert_singleton_facet(
            StyleVisualFacet,
            style_id=style_id,
            payload={
                "facet_version": STYLE_ENRICHMENT_FACET_VERSION,
                "palette_json": visual["palette"],
                "lighting_mood_json": visual["lighting_mood"],
                "photo_treatment_json": visual["photo_treatment"],
                "visual_motifs_json": visual["visual_motifs"],
                "patterns_textures_json": visual["patterns_textures"],
                "platform_visual_cues_json": visual["platform_visual_cues"],
            },
        )
        await self._upsert_singleton_facet(
            StyleFashionItemFacet,
            style_id=style_id,
            payload={
                "facet_version": STYLE_ENRICHMENT_FACET_VERSION,
                "tops_json": fashion_items["tops"],
                "bottoms_json": fashion_items["bottoms"],
                "shoes_json": fashion_items["shoes"],
                "accessories_json": fashion_items["accessories"],
                "hair_makeup_json": fashion_items["hair_makeup"],
                "signature_details_json": fashion_items["signature_details"],
            },
        )
        await self._upsert_singleton_facet(
            StyleImageFacet,
            style_id=style_id,
            payload={
                "facet_version": STYLE_ENRICHMENT_FACET_VERSION,
                "hero_garments_json": image_prompt["hero_garments"],
                "secondary_garments_json": image_prompt["secondary_garments"],
                "core_accessories_json": image_prompt["core_accessories"],
                "props_json": image_prompt["props"],
                "materials_json": image_prompt["materials"],
                "composition_cues_json": image_prompt["composition_cues"],
                "negative_constraints_json": image_prompt["negative_constraints"],
                "visual_motifs_json": image_prompt["visual_motifs"],
                "lighting_mood_json": image_prompt["lighting_mood"],
                "photo_treatment_json": image_prompt["photo_treatment"],
            },
        )
        await self._upsert_singleton_facet(
            StyleRelationFacet,
            style_id=style_id,
            payload={
                "facet_version": STYLE_ENRICHMENT_FACET_VERSION,
                "related_styles_json": relations["related_styles"],
                "overlap_styles_json": relations["overlap_styles"],
                "preceded_by_json": relations["preceded_by"],
                "succeeded_by_json": relations["succeeded_by"],
                "brands_json": relations["brands"],
                "platforms_json": relations["platforms"],
                "origin_regions_json": relations["origin_regions"],
                "era_json": relations["era"],
            },
        )
        await self._upsert_singleton_facet(
            StylePresentationFacet,
            style_id=style_id,
            payload={
                "facet_version": STYLE_ENRICHMENT_FACET_VERSION,
                "short_explanation": presentation["short_explanation"],
                "one_sentence_description": presentation["one_sentence_description"],
                "what_makes_it_distinct_json": presentation["what_makes_it_distinct"],
            },
        )

    async def _upsert_singleton_facet(
        self,
        model: type[Any],
        *,
        style_id: int,
        payload: dict[str, Any],
    ) -> None:
        result = await self.session.execute(
            select(model)
            .where(
                model.style_id == style_id,
                model.facet_version == payload["facet_version"],
            )
            .limit(1)
        )
        instance = result.scalar_one_or_none()
        if instance is None:
            instance = model(style_id=style_id, **payload)
        else:
            for key, value in payload.items():
                setattr(instance, key, value)
        self.session.add(instance)
        await self.session.flush()

    async def _write_enrichment_log(
        self,
        *,
        style_id: int,
        source_page_id: int | None,
        provider: str,
        model_name: str,
        status: str,
        raw_response_json: dict[str, Any] | None,
        error_message: str | None,
    ) -> None:
        self.session.add(
            StyleLlmEnrichment(
                style_id=style_id,
                source_page_id=source_page_id,
                provider=provider,
                model_name=model_name,
                prompt_version=STYLE_ENRICHMENT_PROMPT_VERSION,
                schema_version=STYLE_ENRICHMENT_SCHEMA_VERSION,
                status=status,
                raw_response_json=raw_response_json,
                error_message=error_message,
            )
        )
        await self.session.flush()

    def _emit_event(self, event_name: str, payload: dict[str, Any]) -> None:
        if self.progress_reporter is None:
            return
        try:
            self.progress_reporter(event_name, payload)
        except Exception:
            return

    def _emit_run_started(
        self,
        *,
        style_id: int,
        source_page_id: int | None,
        provider: str,
        model_name: str,
    ) -> None:
        payload = build_style_enrichment_run_event_payload(
            style_id=style_id,
            source_page_id=source_page_id,
            provider=provider,
            model_name=model_name,
            status="started",
            attempts=0,
            did_write=False,
            dry_run=not self.write_enabled,
        )
        self._emit_event("style_enrichment_run_started", payload)

    def _emit_run_finished(
        self,
        *,
        style_id: int,
        source_page_id: int | None,
        provider: str,
        model_name: str,
        status: str,
        attempts: int,
        did_write: bool,
        error_class: str | None,
        error_message: str | None,
    ) -> None:
        payload = build_style_enrichment_run_event_payload(
            style_id=style_id,
            source_page_id=source_page_id,
            provider=provider,
            model_name=model_name,
            status=status,
            attempts=attempts,
            did_write=did_write,
            dry_run=not self.write_enabled,
            error_class=error_class,
            error_message=error_message,
        )
        self._emit_event("style_enrichment_run_finished", payload)
        self._emit_event("style_enrichment_metric", build_style_enrichment_run_metric_payload(payload))

    def _build_failure_payload(self, *, completion: ChatGptStructuredCompletion | None) -> dict[str, Any] | None:
        if completion is None:
            return None
        return {
            "raw_content": completion.raw_content,
            "payload": completion.payload,
        }
