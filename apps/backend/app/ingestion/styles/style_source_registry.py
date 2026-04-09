from __future__ import annotations

import re
from urllib.parse import quote, urlparse

from app.ingestion.styles.contracts import (
    DiscoveredStyleCandidate,
    SourceCrawlPolicy,
    StyleSourceRegistry,
    StyleSourceRegistryEntry,
)


KNOWN_NON_STYLE_PREFIXES = (
    "category:",
    "template:",
    "user:",
    "user blog:",
    "special:",
    "help:",
    "file:",
    "forum:",
    "blog:",
)

KNOWN_NON_STYLE_TITLES = {
    "list of aesthetics",
    "aesthetics wiki",
    "home",
    "main page",
    "community",
}

DEFAULT_CRAWL_POLICY = SourceCrawlPolicy(
    user_agent="PortfolioStyleIngestionBot/1.0 (+contact: internal-admin)",
    respect_robots_txt=True,
    robots_txt_url="https://aesthetics.fandom.com/robots.txt",
    min_delay_seconds=20.0,
    max_delay_seconds=40.0,
    jitter_ratio=0.3,
    empty_body_cooldown_min_seconds=900.0,
    empty_body_cooldown_max_seconds=1800.0,
    blocked_after_consecutive_empty=3,
    max_retries=3,
    retry_backoff_seconds=30.0,
    max_concurrency=1,
)


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _is_candidate_title(title: str) -> bool:
    cleaned = _clean_text(title)
    lowered = cleaned.lower()
    if not cleaned or lowered in KNOWN_NON_STYLE_TITLES:
        return False
    if any(lowered.startswith(prefix) for prefix in KNOWN_NON_STYLE_PREFIXES):
        return False
    if ":" in cleaned:
        return False
    return True


class AestheticsWikiSourceRegistry(StyleSourceRegistry):
    def __init__(self) -> None:
        self._sources = (
            StyleSourceRegistryEntry(
                source_name="aesthetics_wiki",
                source_site="aesthetics.fandom.com",
                index_url="https://aesthetics.fandom.com/wiki/List_of_Aesthetics",
                discovery_page_titles=(
                    "List of Aesthetics",
                    "Category:Aesthetics by Family",
                    "Category:Aesthetics by Type",
                    "Category:Aesthetics by Color",
                    "Category:Aesthetics by Decade",
                    "Category:Aesthetics by Origin",
                ),
                allowed_domains=("aesthetics.fandom.com",),
                parser_version="0.2.0",
                normalizer_version="0.2.0",
                crawl_policy=DEFAULT_CRAWL_POLICY,
                discovery_fetch_mode="mediawiki_action_api",
                detail_fetch_mode="mediawiki_action_api",
                api_endpoint_url="https://aesthetics.fandom.com/api.php",
            ),
        )

    def list_sources(self) -> tuple[StyleSourceRegistryEntry, ...]:
        return self._sources

    def get_source(self, source_name: str) -> StyleSourceRegistryEntry:
        for source in self._sources:
            if source.source_name == source_name:
                return source
        available = ", ".join(source.source_name for source in self._sources)
        raise ValueError(f"Unknown source_name={source_name!r}. Available: {available}")

    def discover_style_candidates(
        self,
        *,
        source: StyleSourceRegistryEntry,
        discovery_payload: object,
    ) -> tuple[DiscoveredStyleCandidate, ...]:
        if source.discovery_fetch_mode == "mediawiki_action_api":
            return self._discover_from_mediawiki_parse_links(source=source, discovery_payload=discovery_payload)

        raise NotImplementedError(
            f"Discovery fetch mode {source.discovery_fetch_mode!r} is not implemented for source "
            f"{source.source_name!r}"
        )

    def _discover_from_mediawiki_parse_links(
        self,
        *,
        source: StyleSourceRegistryEntry,
        discovery_payload: object,
    ) -> tuple[DiscoveredStyleCandidate, ...]:
        if not isinstance(discovery_payload, dict):
            raise ValueError(
                f"MediaWiki discovery payload for source {source.source_name!r} must be dict, "
                f"got {type(discovery_payload).__name__}"
            )

        pages = discovery_payload.get("pages")
        if not isinstance(pages, list) or not pages:
            raise ValueError(
                f"MediaWiki discovery payload for source {source.source_name!r} does not contain pages array"
            )

        candidates: dict[str, DiscoveredStyleCandidate] = {}
        for parse_node in pages:
            if not isinstance(parse_node, dict):
                continue

            links = parse_node.get("links")
            if not isinstance(links, list):
                continue

            for item in links:
                if not isinstance(item, dict):
                    continue

                namespace = item.get("ns")
                if namespace != 0:
                    continue

                source_title = item.get("title") or item.get("*")
                if not isinstance(source_title, str):
                    continue
                source_title = _clean_text(source_title)
                if not _is_candidate_title(source_title):
                    continue

                candidate = DiscoveredStyleCandidate(
                    source_name=source.source_name,
                    source_site=source.source_site,
                    source_title=source_title,
                    source_url=self.build_candidate_url(source=source, source_title=source_title),
                )
                candidates[candidate.source_url] = candidate

        return tuple(
            sorted(
                candidates.values(),
                key=lambda item: (item.source_title.casefold(), item.source_url),
            )
        )

    def build_candidate_url(
        self,
        *,
        source: StyleSourceRegistryEntry,
        source_title: str,
    ) -> str:
        normalized_title = _clean_text(source_title).replace(" ", "_")
        encoded_title = quote(normalized_title, safe="()'_,!-")
        parsed = urlparse(source.index_url)
        return f"{parsed.scheme}://{parsed.netloc}/wiki/{encoded_title}"
