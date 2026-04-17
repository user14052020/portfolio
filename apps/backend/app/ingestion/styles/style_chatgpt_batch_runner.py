from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.styles.contracts import (
    BatchEnrichmentResult,
    StyleChatGptEnrichmentBatchRunner,
    StyleEnrichmentBatchItem,
)
from app.ingestion.styles.style_chatgpt_enrichment_service import DefaultStyleChatGptEnrichmentService
from app.ingestion.styles.style_chatgpt_prompt_builder import STYLE_ENRICHMENT_FACET_VERSION
from app.models import (
    Style,
    StyleFashionItemFacet,
    StyleImageFacet,
    StyleKnowledgeFacet,
    StyleLlmEnrichment,
    StylePresentationFacet,
    StyleRelationFacet,
    StyleVisualFacet,
)


FAILED_ENRICHMENT_STATUSES = frozenset({"failed_transport", "failed_validation", "failed_write"})


class DefaultStyleChatGptEnrichmentBatchRunner(StyleChatGptEnrichmentBatchRunner):
    def __init__(
        self,
        *,
        session_factory: Callable[[], Any],
        service_factory: Callable[..., DefaultStyleChatGptEnrichmentService] | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.service_factory = service_factory or DefaultStyleChatGptEnrichmentService

    async def run(
        self,
        *,
        style_ids: list[int] | None = None,
        limit: int | None = None,
        offset: int = 0,
        dry_run: bool = False,
        overwrite_existing: bool = False,
    ) -> BatchEnrichmentResult:
        targets = await self._load_target_styles(style_ids=style_ids, limit=limit, offset=offset)
        items: list[StyleEnrichmentBatchItem] = []
        processed_count = 0
        succeeded_count = 0
        failed_count = 0
        skipped_existing_count = 0

        for style in targets:
            async with self.session_factory() as session:
                if not overwrite_existing and await self._is_already_enriched(session, style_id=style.id):
                    items.append(
                        StyleEnrichmentBatchItem(
                            style_id=style.id,
                            style_slug=style.slug,
                            status="skipped_existing",
                            did_write=False,
                            error_message=None,
                            source_page_id=None,
                        )
                    )
                    skipped_existing_count += 1
                    continue

                service = self.service_factory(session=session, write_enabled=not dry_run)
                try:
                    result = await service.enrich_style(style.id)
                    if dry_run:
                        await session.rollback()
                    else:
                        await session.commit()
                    items.append(
                        StyleEnrichmentBatchItem(
                            style_id=result.style_id,
                            style_slug=result.style_slug,
                            status=result.status,
                            did_write=result.did_write,
                            error_message=result.error_message,
                            source_page_id=result.source_page_id,
                        )
                    )
                    processed_count += 1
                    succeeded_count += 1
                except Exception as exc:  # noqa: BLE001
                    await session.rollback()
                    items.append(
                        StyleEnrichmentBatchItem(
                            style_id=style.id,
                            style_slug=style.slug,
                            status="failed",
                            did_write=False,
                            error_message=str(exc),
                            source_page_id=None,
                        )
                    )
                    processed_count += 1
                    failed_count += 1

        return BatchEnrichmentResult(
            selected_count=len(targets),
            processed_count=processed_count,
            succeeded_count=succeeded_count,
            failed_count=failed_count,
            skipped_existing_count=skipped_existing_count,
            dry_run=dry_run,
            overwrite_existing=overwrite_existing,
            items=tuple(items),
        )

    async def run_retry_failed(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        dry_run: bool = False,
        overwrite_existing: bool = False,
    ) -> BatchEnrichmentResult:
        style_ids = await self._load_retry_failed_style_ids(limit=limit, offset=offset)
        return await self.run(
            style_ids=style_ids,
            limit=None,
            offset=0,
            dry_run=dry_run,
            overwrite_existing=overwrite_existing,
        )

    async def _load_target_styles(
        self,
        *,
        style_ids: list[int] | None,
        limit: int | None,
        offset: int,
    ) -> list[Style]:
        safe_offset = max(offset, 0)
        async with self.session_factory() as session:
            if style_ids:
                unique_style_ids: list[int] = []
                seen: set[int] = set()
                for item in style_ids:
                    if item in seen:
                        continue
                    seen.add(item)
                    unique_style_ids.append(item)
                result = await session.execute(select(Style).where(Style.id.in_(unique_style_ids)))
                style_map = {style.id: style for style in result.scalars().all()}
                return [style_map[item] for item in unique_style_ids if item in style_map]

            statement = select(Style).where(Style.status != "archived").order_by(Style.id.asc()).offset(safe_offset)
            if limit is not None:
                statement = statement.limit(limit)
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def _load_retry_failed_style_ids(self, *, limit: int | None, offset: int) -> list[int]:
        safe_offset = max(offset, 0)
        async with self.session_factory() as session:
            latest_log_subquery = (
                select(
                    StyleLlmEnrichment.style_id.label("style_id"),
                    func.max(StyleLlmEnrichment.id).label("latest_log_id"),
                )
                .group_by(StyleLlmEnrichment.style_id)
                .subquery()
            )
            statement = (
                select(StyleLlmEnrichment.style_id)
                .join(latest_log_subquery, StyleLlmEnrichment.id == latest_log_subquery.c.latest_log_id)
                .where(StyleLlmEnrichment.status.in_(tuple(FAILED_ENRICHMENT_STATUSES)))
                .order_by(StyleLlmEnrichment.style_id.asc())
                .offset(safe_offset)
            )
            if limit is not None:
                statement = statement.limit(limit)
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def _is_already_enriched(self, session: AsyncSession, *, style_id: int) -> bool:
        facet_models = (
            StyleKnowledgeFacet,
            StyleVisualFacet,
            StyleFashionItemFacet,
            StyleImageFacet,
            StyleRelationFacet,
            StylePresentationFacet,
        )
        for model in facet_models:
            result = await session.execute(
                select(model.id)
                .where(
                    model.style_id == style_id,
                    model.facet_version == STYLE_ENRICHMENT_FACET_VERSION,
                )
                .limit(1)
            )
            if result.scalar_one_or_none() is None:
                return False
        return True
