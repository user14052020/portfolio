from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class SourceCrawlPolicy:
    user_agent: str
    respect_robots_txt: bool = True
    robots_txt_url: str | None = None
    min_delay_seconds: float = 2.0
    max_delay_seconds: float = 4.0
    max_retries: int = 3
    retry_backoff_seconds: float = 5.0
    max_concurrency: int = 1


@dataclass(frozen=True)
class StyleSourceRegistryEntry:
    source_name: str
    source_site: str
    index_url: str
    allowed_domains: tuple[str, ...]
    parser_version: str
    normalizer_version: str
    crawl_policy: SourceCrawlPolicy


@dataclass(frozen=True)
class DiscoveredStyleCandidate:
    source_name: str
    source_site: str
    source_title: str
    source_url: str


@dataclass(frozen=True)
class ScrapedStylePage:
    source_name: str
    source_site: str
    source_title: str
    source_url: str
    fetched_at: datetime
    raw_html: str


@dataclass(frozen=True)
class NormalizedSection:
    section_order: int
    section_title: str | None
    section_level: int | None
    section_text: str
    section_hash: str


@dataclass(frozen=True)
class NormalizedLink:
    anchor_text: str | None
    target_title: str | None
    target_url: str
    link_type: str


@dataclass(frozen=True)
class NormalizedImage:
    image_url: str
    caption: str | None
    alt_text: str | None
    position: int
    license_if_available: str | None = None


@dataclass(frozen=True)
class NormalizedStyleDocument:
    source_name: str
    source_site: str
    source_title: str
    source_url: str
    fetched_at: datetime
    raw_html: str
    raw_text: str
    source_hash: str
    sections: tuple[NormalizedSection, ...]
    links: tuple[NormalizedLink, ...]
    images: tuple[NormalizedImage, ...]
    parser_version: str
    normalizer_version: str


@dataclass(frozen=True)
class TraitSeed:
    trait_type: str
    trait_value: str
    weight: float = 1.0
    evidence_kind: str = "derived_summary"
    evidence_text: str | None = None


@dataclass(frozen=True)
class TaxonomyLinkSeed:
    taxonomy_type: str
    name: str
    slug: str
    description: str | None = None
    link_strength: float = 1.0
    evidence_kind: str = "derived_summary"
    evidence_text: str | None = None


@dataclass(frozen=True)
class StyleRelationSeed:
    target_style_slug: str
    relation_type: str
    score: float = 1.0
    reason: str | None = None
    evidence_kind: str = "derived_summary"
    evidence_text: str | None = None


@dataclass(frozen=True)
class EnrichedStyleDocument:
    normalized: NormalizedStyleDocument
    canonical_name: str
    slug: str
    display_name: str
    short_definition: str | None
    long_summary: str | None
    alias_candidates: tuple[str, ...]
    profile_payload: dict[str, Any]
    confidence_score: float = 0.0
    trait_seeds: tuple[TraitSeed, ...] = ()
    taxonomy_link_seeds: tuple[TaxonomyLinkSeed, ...] = ()
    relation_seeds: tuple[StyleRelationSeed, ...] = ()


@dataclass(frozen=True)
class ValidatedStyleDocument:
    enriched: EnrichedStyleDocument
    is_valid: bool
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class StylePersistencePayload:
    source_record: dict[str, Any]
    section_records: tuple[dict[str, Any], ...]
    link_records: tuple[dict[str, Any], ...]
    style_record: dict[str, Any]
    alias_records: tuple[dict[str, Any], ...]
    profile_record: dict[str, Any]
    trait_records: tuple[dict[str, Any], ...]
    taxonomy_records: tuple[dict[str, Any], ...]
    relation_records: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class StylePersistenceResult:
    source_id: int
    style_id: int
    style_slug: str
    was_source_created: bool = False
    was_style_created: bool = False
    was_style_updated: bool = False


@dataclass(frozen=True)
class CandidateBatchSelection:
    source: StyleSourceRegistryEntry
    discovered_count: int
    selected_count: int
    candidates: tuple[DiscoveredStyleCandidate, ...]


@dataclass(frozen=True)
class CandidateBatchFailure:
    source_title: str
    source_url: str
    error: str


@dataclass(frozen=True)
class StyleDirectionMatchOption:
    style_direction_id: int
    style_direction_slug: str
    style_direction_title: str
    match_method: str
    match_score: float


@dataclass(frozen=True)
class StyleDirectionMatchDecision:
    source_name: str
    source_url: str
    source_title: str
    discovered_slug: str
    match_status: str
    matched_style_direction_id: int | None = None
    match_method: str | None = None
    match_score: float = 0.0
    candidate_count: int = 0
    candidate_options: tuple[StyleDirectionMatchOption, ...] = ()


@dataclass(frozen=True)
class StyleDirectionReviewQueueItem:
    review_id: int
    match_id: int
    source_name: str
    source_url: str
    source_title: str
    discovered_slug: str
    review_status: str
    match_status: str
    queued_at: datetime
    candidate_count: int = 0
    candidate_options: tuple[StyleDirectionMatchOption, ...] = ()


@dataclass(frozen=True)
class StyleDirectionReviewResolutionResult:
    review_id: int
    match_id: int
    source_name: str
    source_url: str
    source_title: str
    discovered_slug: str
    review_status: str
    match_status: str
    selected_style_direction_id: int | None = None
    resolution_type: str | None = None


@dataclass(frozen=True)
class StyleDirectionMergeItem:
    match_id: int
    source_name: str
    source_url: str
    source_title: str
    discovered_slug: str
    match_status: str
    style_direction_id: int | None
    canonical_style_id: int | None
    canonical_style_slug: str | None
    merge_status: str
    link_status: str | None = None
    confidence_score: float = 0.0


@dataclass(frozen=True)
class StyleDirectionMergeReport:
    selected_count: int
    merged_count: int
    skipped_count: int
    items: tuple[StyleDirectionMergeItem, ...] = ()


@dataclass(frozen=True)
class BatchIngestionReport:
    source_name: str
    discovered_count: int
    selected_count: int
    processed_count: int
    created_count: int
    updated_count: int
    failed_count: int
    failures: tuple[CandidateBatchFailure, ...] = ()


@dataclass(frozen=True)
class MatchBatchReport:
    source_name: str
    discovered_count: int
    selected_count: int
    auto_matched_count: int
    ambiguous_count: int
    unmatched_count: int
    decisions: tuple[StyleDirectionMatchDecision, ...] = ()


@dataclass
class StyleIngestionCounters:
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    styles_seen: int = 0
    styles_matched: int = 0
    styles_created: int = 0
    styles_updated: int = 0
    styles_failed: int = 0


class StyleSourceRegistry(Protocol):
    def list_sources(self) -> tuple[StyleSourceRegistryEntry, ...]:
        ...

    def get_source(self, source_name: str) -> StyleSourceRegistryEntry:
        ...

    def discover_style_candidates(
        self,
        *,
        source: StyleSourceRegistryEntry,
        index_html: str,
    ) -> tuple[DiscoveredStyleCandidate, ...]:
        ...

    def build_candidate_url(
        self,
        *,
        source: StyleSourceRegistryEntry,
        source_title: str,
    ) -> str:
        ...


class StyleScraper(Protocol):
    async def fetch_index_html(self, source: StyleSourceRegistryEntry) -> str:
        ...

    async def fetch_style_page(
        self,
        source: StyleSourceRegistryEntry,
        candidate: DiscoveredStyleCandidate,
    ) -> ScrapedStylePage:
        ...


class StyleNormalizer(Protocol):
    def normalize_page(
        self,
        source: StyleSourceRegistryEntry,
        page: ScrapedStylePage,
    ) -> NormalizedStyleDocument:
        ...


class StyleEnricher(Protocol):
    def enrich(self, normalized: NormalizedStyleDocument) -> EnrichedStyleDocument:
        ...


class StyleValidator(Protocol):
    def validate(self, enriched: EnrichedStyleDocument) -> ValidatedStyleDocument:
        ...


class StyleDBWriter(Protocol):
    async def persist(self, payload: StylePersistencePayload) -> StylePersistenceResult:
        ...
