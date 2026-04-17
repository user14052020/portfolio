from __future__ import annotations

from app.ingestion.styles.contracts import (
    CandidateRemoteState,
    DiscoveredStyleCandidate,
    ScrapedStylePage,
    StyleScraper,
    StyleSourceRegistryEntry,
)
from app.ingestion.styles.style_fetchers import MediaWikiApiFetcher, PoliteHTTPTransport, StyleFetchEventReporter


class HTTPStyleScraper(StyleScraper):
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        session_factory: object | None = None,
        event_reporter: StyleFetchEventReporter | None = None,
    ) -> None:
        transport = PoliteHTTPTransport(
            timeout_seconds=timeout_seconds,
            session_factory=session_factory,
            event_reporter=event_reporter,
        )
        self.mediawiki_api_fetcher = MediaWikiApiFetcher(transport=transport)

    async def fetch_discovery_payload(self, source: StyleSourceRegistryEntry) -> object:
        if source.discovery_fetch_mode == "mediawiki_action_api":
            return await self.mediawiki_api_fetcher.fetch_discovery_payload(source)
        raise NotImplementedError(
            f"Discovery fetch mode {source.discovery_fetch_mode!r} is not implemented yet for source "
            f"{source.source_name!r}"
        )

    async def fetch_candidate_remote_states(
        self,
        source: StyleSourceRegistryEntry,
        candidates: tuple[DiscoveredStyleCandidate, ...],
    ) -> tuple[CandidateRemoteState, ...]:
        if source.detail_fetch_mode == "mediawiki_action_api":
            return await self.mediawiki_api_fetcher.fetch_candidate_remote_states(source, candidates)
        raise NotImplementedError(
            f"Detail fetch mode {source.detail_fetch_mode!r} is not implemented for source {source.source_name!r}"
        )

    async def fetch_style_page(
        self,
        source: StyleSourceRegistryEntry,
        candidate: DiscoveredStyleCandidate,
    ) -> ScrapedStylePage:
        if source.detail_fetch_mode == "mediawiki_action_api":
            return await self.mediawiki_api_fetcher.fetch_style_page(source, candidate)
        raise NotImplementedError(
            f"Detail fetch mode {source.detail_fetch_mode!r} is not implemented for source {source.source_name!r}"
        )
