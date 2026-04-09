from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.ingestion.styles.contracts import (
    BatchIngestionReport,
    CandidateBatchFailure,
    CandidateBatchSelection,
    DiscoveredStyleCandidate,
    StyleEnricher,
    StyleNormalizer,
    StyleScraper,
    StyleSourceRegistryEntry,
    StyleSourceRegistry,
    StyleValidator,
)
from app.ingestion.styles.runner import StyleIngestionRunner
from app.ingestion.styles.style_db_writer import SQLAlchemyStyleDBWriter
from app.models.style_ingest_run import StyleIngestRun


DEFAULT_BATCH_LIMIT = 20
MAX_SAFE_BATCH_LIMIT = 100


class StyleBatchIngestionRunner:
    def __init__(
        self,
        *,
        registry: StyleSourceRegistry,
        scraper: StyleScraper,
        normalizer: StyleNormalizer,
        enricher: StyleEnricher,
        validator: StyleValidator,
        session_factory: Callable[[], Any],
    ) -> None:
        self.registry = registry
        self.scraper = scraper
        self.normalizer = normalizer
        self.enricher = enricher
        self.validator = validator
        self.session_factory = session_factory

    async def discover_candidates(
        self,
        *,
        source_name: str,
        title_contains: str | None = None,
        offset: int = 0,
        limit: int = DEFAULT_BATCH_LIMIT,
    ) -> CandidateBatchSelection:
        safe_limit = self._validate_limit(limit)
        safe_offset = max(offset, 0)
        source = self.registry.get_source(source_name)
        discovery_payload = await self.scraper.fetch_discovery_payload(source)
        discovered = self.registry.discover_style_candidates(source=source, discovery_payload=discovery_payload)
        if not discovered:
            raise RuntimeError(
                f"Trusted source index returned zero style candidates for source {source.source_name!r}. "
                "Batch discovery cannot continue without a valid source index."
            )
        filtered = self._filter_candidates(
            discovered,
            title_contains=title_contains,
            offset=safe_offset,
            limit=safe_limit,
        )
        return CandidateBatchSelection(
            source=source,
            discovered_count=len(discovered),
            selected_count=len(filtered),
            candidates=filtered,
            discovery_payload=discovery_payload,
        )

    async def run_batch(
        self,
        *,
        selection: CandidateBatchSelection,
        run_id: int,
        start_index: int = 0,
        processed_count: int = 0,
        created_count: int = 0,
        updated_count: int = 0,
        failed_count: int = 0,
    ) -> BatchIngestionReport:
        failures: list[CandidateBatchFailure] = []

        for index, candidate in enumerate(selection.candidates[start_index:], start=start_index):
            try:
                async with self.session_factory() as session:
                    writer = SQLAlchemyStyleDBWriter(session, run_id=run_id)
                    runner = StyleIngestionRunner(
                        scraper=self.scraper,
                        normalizer=self.normalizer,
                        enricher=self.enricher,
                        validator=self.validator,
                        writer=writer,
                    )
                    _, result = await runner.process_and_persist(source=selection.source, candidate=candidate)
                    await session.commit()
                processed_count += 1
                if result.was_style_created:
                    created_count += 1
                if result.was_style_updated:
                    updated_count += 1
                await self._update_batch_checkpoint(
                    run_id=run_id,
                    next_index=index + 1,
                    processed_count=processed_count,
                    created_count=created_count,
                    updated_count=updated_count,
                    failed_count=failed_count,
                    last_candidate=candidate,
                    last_error=None,
                )
            except Exception as exc:
                failed_count += 1
                failures.append(
                    CandidateBatchFailure(
                        source_title=candidate.source_title,
                        source_url=candidate.source_url,
                        error=str(exc),
                    )
                )
                await self._update_batch_checkpoint(
                    run_id=run_id,
                    next_index=index + 1,
                    processed_count=processed_count,
                    created_count=created_count,
                    updated_count=updated_count,
                    failed_count=failed_count,
                    last_candidate=candidate,
                    last_error=str(exc),
                )

        return BatchIngestionReport(
            source_name=selection.source.source_name,
            discovered_count=selection.discovered_count,
            selected_count=selection.selected_count,
            processed_count=processed_count,
            created_count=created_count,
            updated_count=updated_count,
            failed_count=failed_count,
            failures=tuple(failures),
        )

    async def _update_batch_checkpoint(
        self,
        *,
        run_id: int,
        next_index: int,
        processed_count: int,
        created_count: int,
        updated_count: int,
        failed_count: int,
        last_candidate: DiscoveredStyleCandidate,
        last_error: str | None = None,
    ) -> None:
        async with self.session_factory() as session:
            run = await session.get(StyleIngestRun, run_id)
            if run is None:
                return
            checkpoint = dict(run.checkpoint_json or {})
            checkpoint.update(
                {
                    "next_index": next_index,
                    "processed_count": processed_count,
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "failed_count": failed_count,
                    "last_attempted_source_title": last_candidate.source_title,
                    "last_attempted_source_url": last_candidate.source_url,
                    "last_error": last_error,
                }
            )
            run.checkpoint_json = checkpoint
            run.run_status = "running"
            await session.commit()

    def _filter_candidates(
        self,
        candidates: tuple[DiscoveredStyleCandidate, ...],
        *,
        title_contains: str | None,
        offset: int,
        limit: int,
    ) -> tuple[DiscoveredStyleCandidate, ...]:
        filtered = list(candidates)
        if title_contains:
            needle = title_contains.casefold().strip()
            filtered = [item for item in filtered if needle in item.source_title.casefold()]
        return tuple(filtered[offset : offset + limit])

    def _validate_limit(self, limit: int) -> int:
        if limit <= 0:
            raise ValueError("Batch limit must be greater than 0")
        if limit > MAX_SAFE_BATCH_LIMIT:
            raise ValueError(
                f"Batch limit {limit} exceeds safe maximum {MAX_SAFE_BATCH_LIMIT}. "
                "Increase the batch gradually to avoid aggressive crawling."
            )
        return limit
