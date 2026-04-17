from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol


StyleDiscoveryFetchMode = Literal["mediawiki_action_api"]
StyleDetailFetchMode = Literal["mediawiki_action_api"]


@dataclass(frozen=True)
class SourceCrawlPolicy:
    user_agent: str
    min_delay_seconds: float = 2.0
    max_delay_seconds: float = 4.0
    jitter_ratio: float = 0.3
    empty_body_cooldown_min_seconds: float = 900.0
    empty_body_cooldown_max_seconds: float = 1800.0
    blocked_after_consecutive_empty: int = 3
    max_retries: int = 3
    retry_backoff_seconds: float = 5.0
    retry_backoff_jitter_seconds: float = 1.0
    max_concurrency: int = 1


@dataclass(frozen=True)
class StyleSourceRegistryEntry:
    source_name: str
    source_site: str
    index_url: str
    discovery_page_titles: tuple[str, ...]
    allowed_domains: tuple[str, ...]
    parser_version: str
    normalizer_version: str
    crawl_policy: SourceCrawlPolicy
    discovery_fetch_mode: StyleDiscoveryFetchMode = "mediawiki_action_api"
    detail_fetch_mode: StyleDetailFetchMode = "mediawiki_action_api"
    api_endpoint_url: str | None = None


@dataclass(frozen=True)
class DiscoveredStyleCandidate:
    source_name: str
    source_site: str
    source_title: str
    source_url: str


@dataclass(frozen=True)
class CandidateRemoteState:
    source_name: str
    source_title: str
    source_url: str
    remote_page_id: int | None = None
    remote_revision_id: int | None = None


@dataclass(frozen=True)
class ScrapedStylePage:
    source_name: str
    source_site: str
    source_title: str
    source_url: str
    fetched_at: datetime
    raw_html: str
    fetch_mode: StyleDetailFetchMode = "mediawiki_action_api"
    page_id: int | None = None
    revision_id: int | None = None
    raw_wikitext: str | None = None


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
    section_title: str | None = None


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
    fetch_mode: StyleDetailFetchMode
    page_id: int | None
    revision_id: int | None
    raw_html: str
    raw_wikitext: str | None
    raw_text: str
    source_hash: str
    content_fingerprint: str | None
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
    discovery_payload: object | None = None


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
class QueuedJobBatchReport:
    source_name: str
    discovered_count: int | None
    selected_count: int | None
    enqueued_count: int
    reused_count: int
    queued_job_id: int | None = None
    queued_job_type: str | None = None


@dataclass(frozen=True)
class ProcessedIngestJobResult:
    job_id: int
    job_type: str
    status: str
    source_name: str
    source_title: str | None = None
    source_url: str | None = None
    source_page_id: int | None = None
    source_page_version_id: int | None = None
    style_id: int | None = None
    style_slug: str | None = None
    detail_job_id: int | None = None
    normalize_job_id: int | None = None
    error_class: str | None = None
    error_message: str | None = None
    cooldown_until: datetime | None = None
    discovered_count: int | None = None
    selected_count: int | None = None
    enqueued_count: int | None = None
    reused_count: int | None = None
    was_style_created: bool = False
    was_style_updated: bool = False
    persist_outcome: str | None = None


@dataclass(frozen=True)
class IngestWorkerRunReport:
    source_name: str
    processed_jobs: int
    succeeded_jobs: int
    requeued_jobs: int
    cooldown_deferred_jobs: int
    soft_failed_jobs: int
    hard_failed_jobs: int
    idle_polls: int
    stopped_reason: str
    created_styles_count: int = 0
    updated_styles_count: int = 0
    skipped_styles_count: int = 0
    last_job_id: int | None = None
    last_job_type: str | None = None
    last_status: str | None = None


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


@dataclass(frozen=True)
class StyleEnrichmentResult:
    style_id: int
    style_slug: str
    source_page_id: int | None
    provider: str
    model_name: str
    prompt_version: str
    schema_version: str
    status: str
    attempts: int
    did_write: bool
    validation_errors: tuple[str, ...] = ()
    error_message: str | None = None


@dataclass(frozen=True)
class StyleEnrichmentBatchItem:
    style_id: int
    style_slug: str | None
    status: str
    did_write: bool
    error_message: str | None = None
    source_page_id: int | None = None


@dataclass(frozen=True)
class BatchEnrichmentResult:
    selected_count: int
    processed_count: int
    succeeded_count: int
    failed_count: int
    skipped_existing_count: int
    dry_run: bool
    overwrite_existing: bool
    items: tuple[StyleEnrichmentBatchItem, ...] = ()


class StyleSourceRegistry(Protocol):
    def list_sources(self) -> tuple[StyleSourceRegistryEntry, ...]:
        ...

    def get_source(self, source_name: str) -> StyleSourceRegistryEntry:
        ...

    def discover_style_candidates(
        self,
        *,
        source: StyleSourceRegistryEntry,
        discovery_payload: object,
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
    async def fetch_discovery_payload(self, source: StyleSourceRegistryEntry) -> object:
        ...

    async def fetch_candidate_remote_states(
        self,
        source: StyleSourceRegistryEntry,
        candidates: tuple[DiscoveredStyleCandidate, ...],
    ) -> tuple[CandidateRemoteState, ...]:
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


class StyleChatGptEnrichmentService(Protocol):
    async def enrich_style(self, style_id: int) -> StyleEnrichmentResult:
        ...


class StyleChatGptEnrichmentBatchRunner(Protocol):
    async def run(
        self,
        *,
        style_ids: list[int] | None = None,
        limit: int | None = None,
        offset: int = 0,
        dry_run: bool = False,
        overwrite_existing: bool = False,
    ) -> BatchEnrichmentResult:
        ...
