from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlparse

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
    min_delay_seconds=2.5,
    max_delay_seconds=5.0,
    max_retries=3,
    retry_backoff_seconds=8.0,
    max_concurrency=1,
)


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _decode_wiki_title(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or ""
    if "/wiki/" not in path:
        return ""
    slug = path.split("/wiki/", 1)[1]
    slug = unquote(slug).replace("_", " ")
    return _clean_text(slug)


def _is_candidate_path(url: str, *, source: StyleSourceRegistryEntry) -> bool:
    parsed = urlparse(url)
    if parsed.netloc and not any(parsed.netloc.endswith(domain) for domain in source.allowed_domains):
        return False
    if "/wiki/" not in parsed.path:
        return False
    title = _decode_wiki_title(url)
    lowered = title.lower()
    if not title or lowered in KNOWN_NON_STYLE_TITLES:
        return False
    if any(lowered.startswith(prefix) for prefix in KNOWN_NON_STYLE_PREFIXES):
        return False
    if ":" in title:
        return False
    return True


class _AestheticsWikiIndexParser(HTMLParser):
    def __init__(self, *, source: StyleSourceRegistryEntry) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self._current_href: str | None = None
        self._anchor_parts: list[str] = []
        self._candidates: dict[str, DiscoveredStyleCandidate] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_map = dict(attrs)
        href = attrs_map.get("href")
        if not href:
            return
        absolute_url = urljoin(self.source.index_url, href)
        if not _is_candidate_path(absolute_url, source=self.source):
            return
        self._current_href = absolute_url
        self._anchor_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href is None:
            return
        cleaned = _clean_text(data)
        if cleaned:
            self._anchor_parts.append(cleaned)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return
        source_title = _clean_text(" ".join(self._anchor_parts)) or _decode_wiki_title(self._current_href)
        if source_title:
            candidate = DiscoveredStyleCandidate(
                source_name=self.source.source_name,
                source_site=self.source.source_site,
                source_title=source_title,
                source_url=self._current_href,
            )
            self._candidates[candidate.source_url] = candidate
        self._current_href = None
        self._anchor_parts = []

    def finalize(self) -> tuple[DiscoveredStyleCandidate, ...]:
        return tuple(
            sorted(
                self._candidates.values(),
                key=lambda item: (item.source_title.casefold(), item.source_url),
            )
        )


class AestheticsWikiSourceRegistry(StyleSourceRegistry):
    def __init__(self) -> None:
        self._sources = (
            StyleSourceRegistryEntry(
                source_name="aesthetics_wiki",
                source_site="aesthetics.fandom.com",
                index_url="https://aesthetics.fandom.com/wiki/List_of_Aesthetics",
                allowed_domains=("aesthetics.fandom.com",),
                parser_version="0.2.0",
                normalizer_version="0.2.0",
                crawl_policy=DEFAULT_CRAWL_POLICY,
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
        index_html: str,
    ) -> tuple[DiscoveredStyleCandidate, ...]:
        parser = _AestheticsWikiIndexParser(source=source)
        parser.feed(index_html)
        return parser.finalize()

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
