from app.ingestion.styles.contracts import (
    DiscoveredStyleCandidate,
    StyleDBWriter,
    StylePersistenceResult,
    StyleEnricher,
    StyleNormalizer,
    StyleScraper,
    StyleSourceRegistryEntry,
    StyleValidator,
    ValidatedStyleDocument,
)
from app.ingestion.styles.style_db_writer import build_style_persistence_payload


class StyleIngestionRunner:
    def __init__(
        self,
        *,
        scraper: StyleScraper,
        normalizer: StyleNormalizer,
        enricher: StyleEnricher,
        validator: StyleValidator,
        writer: StyleDBWriter | None = None,
    ) -> None:
        self.scraper = scraper
        self.normalizer = normalizer
        self.enricher = enricher
        self.validator = validator
        self.writer = writer

    async def process_candidate(
        self,
        *,
        source: StyleSourceRegistryEntry,
        candidate: DiscoveredStyleCandidate,
    ) -> ValidatedStyleDocument:
        scraped_page = await self.scraper.fetch_style_page(source, candidate)
        normalized_page = self.normalizer.normalize_page(source, scraped_page)
        enriched_document = self.enricher.enrich(normalized_page)
        return self.validator.validate(enriched_document)

    async def process_and_persist(
        self,
        *,
        source: StyleSourceRegistryEntry,
        candidate: DiscoveredStyleCandidate,
    ) -> tuple[ValidatedStyleDocument, StylePersistenceResult]:
        if self.writer is None:
            raise RuntimeError("StyleIngestionRunner.writer is not configured")

        document = await self.process_candidate(source=source, candidate=candidate)
        if not document.is_valid:
            raise ValueError("; ".join(document.errors) or "validated style document is invalid")

        payload = build_style_persistence_payload(document)
        result = await self.writer.persist(payload)
        return document, result
