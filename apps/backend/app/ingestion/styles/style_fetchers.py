from __future__ import annotations

import asyncio
import json
import random
import time
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote, unquote, urlparse

import httpx

from app.ingestion.styles.contracts import (
    CandidateRemoteState,
    DiscoveredStyleCandidate,
    ScrapedStylePage,
    StyleSourceRegistryEntry,
)
from app.ingestion.styles.errors import DonorApiError, DonorPayloadError
from app.ingestion.styles.source_fetch_log_service import SourceFetchLogService
from app.ingestion.styles.source_fetch_state_service import SourceFetchStateService


JSON_ACCEPT_HEADER = "application/json,text/javascript,*/*;q=0.8"
StyleFetchEventReporter = Callable[[str, dict[str, object]], None]


def _resolve_mediawiki_title_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or ""
    if "/wiki/" not in path:
        return ""
    slug = path.split("/wiki/", 1)[1]
    return unquote(slug).replace("_", " ").strip()


def _resolve_mediawiki_page_title(candidate: DiscoveredStyleCandidate) -> str:
    return _resolve_mediawiki_title_from_url(candidate.source_url) or candidate.source_title


def _normalize_mediawiki_title_key(title: str) -> str:
    return title.strip().replace("_", " ").casefold()


def _build_mediawiki_page_url(*, index_url: str, title: str) -> str:
    parsed = urlparse(index_url)
    normalized_title = title.strip().replace(" ", "_")
    encoded_title = quote(normalized_title, safe="()'_,!-")
    return f"{parsed.scheme}://{parsed.netloc}/wiki/{encoded_title}"


def _classify_discovery_page_kind(title: str) -> str:
    normalized = _normalize_mediawiki_title_key(title)
    if normalized == "list of aesthetics":
        return "discovery_index"
    if "by family" in normalized:
        return "taxonomy_family"
    if "by type" in normalized:
        return "taxonomy_type"
    if "by color" in normalized or "by colour" in normalized:
        return "taxonomy_color"
    if "by decade" in normalized or "by era" in normalized:
        return "taxonomy_decade"
    if "by origin" in normalized or "by country" in normalized or "by region" in normalized:
        return "taxonomy_origin"
    return "discovery_page"


def _chunked(items: tuple[DiscoveredStyleCandidate, ...], chunk_size: int) -> tuple[tuple[DiscoveredStyleCandidate, ...], ...]:
    if chunk_size <= 0:
        chunk_size = 1
    return tuple(items[index : index + chunk_size] for index in range(0, len(items), chunk_size))


class PoliteHTTPTransport:
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        session_factory: object | None = None,
        event_reporter: StyleFetchEventReporter | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.session_factory = session_factory
        self.event_reporter = event_reporter
        self._last_request_at_by_source: dict[str, datetime] = {}
        self._locks_by_source: dict[str, asyncio.Lock] = {}
        self._fetch_log_service = SourceFetchLogService()
        self._fetch_state_service = SourceFetchStateService()

    def _emit_event(self, event_name: str, **payload: object) -> None:
        if self.event_reporter is None:
            return
        try:
            self.event_reporter(event_name, dict(payload))
        except Exception:
            return

    async def fetch_json(
        self,
        *,
        source: StyleSourceRegistryEntry,
        url: str,
        params: dict[str, str],
        accept: str = JSON_ACCEPT_HEADER,
        fetch_mode: str = "api",
    ) -> dict[str, object]:
        response = await self._send_get(source=source, url=url, params=params, accept=accept, fetch_mode=fetch_mode)
        latency_ms = int(response.extensions.get("style_latency_ms", 0))
        if not response.content.strip():
            self._emit_event(
                "api_request_failed",
                source_name=source.source_name,
                fetch_mode=fetch_mode,
                request_method=response.request.method,
                request_url=str(response.request.url),
                response_status=response.status_code,
                latency_ms=latency_ms,
                error_class="empty_response_body",
            )
            await self._mark_empty_body(source=source, http_status=response.status_code)
            raise DonorPayloadError(
                source_name=source.source_name,
                fetch_mode=fetch_mode,
                request_url=url,
                reason="empty_response_body",
                status_code=response.status_code,
                detail="Donor API returned an empty body for a JSON request",
            )
        try:
            payload = response.json()
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            content_type = response.headers.get("Content-Type")
            content_encoding = response.headers.get("Content-Encoding")
            error = DonorPayloadError(
                source_name=source.source_name,
                fetch_mode=fetch_mode,
                request_url=url,
                reason="invalid_json_response",
                status_code=response.status_code,
                detail=(
                    f"Expected JSON response, got undecodable body; "
                    f"content_type={content_type!r}, content_encoding={content_encoding!r}"
                ),
            )
            self._emit_event(
                "api_request_failed",
                source_name=source.source_name,
                fetch_mode=fetch_mode,
                request_method=response.request.method,
                request_url=str(response.request.url),
                response_status=response.status_code,
                latency_ms=latency_ms,
                error_class=error.reason,
                error_message=error.detail,
            )
            await self._mark_error(source=source, error=error, http_status=response.status_code)
            raise error from exc
        if not isinstance(payload, dict):
            error = DonorPayloadError(
                source_name=source.source_name,
                fetch_mode=fetch_mode,
                request_url=url,
                reason="invalid_json_object",
                status_code=response.status_code,
                detail=f"Expected JSON object, got {type(payload).__name__}",
            )
            self._emit_event(
                "api_request_failed",
                source_name=source.source_name,
                fetch_mode=fetch_mode,
                request_method=response.request.method,
                request_url=str(response.request.url),
                response_status=response.status_code,
                latency_ms=latency_ms,
                error_class=error.reason,
                error_message=error.detail,
            )
            await self._mark_error(source=source, error=error, http_status=response.status_code)
            raise error
        await self._mark_success(source=source, http_status=response.status_code)
        self._emit_event(
            "api_request_succeeded",
            source_name=source.source_name,
            fetch_mode=fetch_mode,
            request_method=response.request.method,
            request_url=str(response.request.url),
            response_status=response.status_code,
            latency_ms=latency_ms,
        )
        return payload

    async def _send_get(
        self,
        *,
        source: StyleSourceRegistryEntry,
        url: str,
        accept: str,
        fetch_mode: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        lock = self._locks_by_source.setdefault(source.source_name, asyncio.Lock())
        async with lock:
            last_error: Exception | None = None
            max_attempts = max(source.crawl_policy.max_retries, 1)

            for attempt in range(1, max_attempts + 1):
                await self._wait_for_turn(source=source, fetch_mode=fetch_mode)
                started = time.perf_counter()
                self._emit_event(
                    "api_request_started",
                    source_name=source.source_name,
                    fetch_mode=fetch_mode,
                    request_method="GET",
                    request_url=url,
                    request_params=params or {},
                    attempt=attempt,
                )
                try:
                    async with httpx.AsyncClient(
                        timeout=self.timeout_seconds,
                        follow_redirects=True,
                        headers=self._build_headers(source=source, accept=accept),
                    ) as client:
                        response = await client.get(url, params=params)
                    await self._persist_response_log(
                        source=source,
                        response=response,
                        fetch_mode=fetch_mode,
                        latency_ms=self._calculate_latency_ms(started),
                        error_class=None,
                    )
                    if response.status_code == 429 or 500 <= response.status_code < 600:
                        self._emit_event(
                            "api_request_failed",
                            source_name=source.source_name,
                            fetch_mode=fetch_mode,
                            request_method=response.request.method,
                            request_url=str(response.request.url),
                            response_status=response.status_code,
                            latency_ms=self._calculate_latency_ms(started),
                            error_class="retryable_http_status",
                            attempt=attempt,
                        )
                        await self._mark_error(
                            source=source,
                            error_class="retryable_http_status",
                            http_status=response.status_code,
                        )
                        await self._handle_retryable_response(
                            source,
                            response,
                            attempt=attempt,
                            fetch_mode=fetch_mode,
                            max_attempts=max_attempts,
                        )
                        last_error = httpx.HTTPStatusError(
                            f"Retryable HTTP status: {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                        continue
                    response.raise_for_status()
                    response.extensions["style_latency_ms"] = self._calculate_latency_ms(started)
                    return response
                except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError, httpx.HTTPStatusError) as exc:
                    await self._persist_error_log(
                        source=source,
                        request_url=url,
                        fetch_mode=fetch_mode,
                        latency_ms=self._calculate_latency_ms(started),
                        error=exc,
                    )
                    last_error = exc
                    response = exc.response if isinstance(exc, httpx.HTTPStatusError) else None
                    request = exc.request if isinstance(exc, httpx.RequestError | httpx.HTTPStatusError) else None
                    self._emit_event(
                        "api_request_failed",
                        source_name=source.source_name,
                        fetch_mode=fetch_mode,
                        request_method=request.method if request is not None else "GET",
                        request_url=str(request.url) if request is not None else url,
                        response_status=response.status_code if response is not None else None,
                        latency_ms=self._calculate_latency_ms(started),
                        error_class=exc.__class__.__name__,
                        error_message=str(exc),
                        attempt=attempt,
                    )
                    await self._mark_error(source=source, error=exc)
                    if attempt >= max_attempts:
                        raise self._build_donor_api_error(
                            source=source,
                            fetch_mode=fetch_mode,
                            request_url=url,
                            error=exc,
                        ) from exc
                    await self._sleep_with_backoff(
                        source,
                        attempt=attempt,
                        fetch_mode=fetch_mode,
                        retry_after_seconds=None,
                    )

            assert last_error is not None
            raise self._build_donor_api_error(
                source=source,
                fetch_mode=fetch_mode,
                request_url=url,
                error=last_error,
            ) from last_error

    async def _wait_for_turn(self, *, source: StyleSourceRegistryEntry, fetch_mode: str) -> None:
        await self._wait_for_state_gate(source=source, fetch_mode=fetch_mode)
        now = datetime.now(UTC)
        last_request_at = self._last_request_at_by_source.get(source.source_name)
        if last_request_at is not None:
            min_delay = float(source.crawl_policy.min_delay_seconds)
            max_delay = float(source.crawl_policy.max_delay_seconds)
            state_interval = await self._load_state_interval(source)
            if state_interval is not None and state_interval > 0:
                jitter_ratio = max(float(source.crawl_policy.jitter_ratio), 0.0)
                jittered_min = state_interval * max(0.0, 1.0 - jitter_ratio)
                jittered_max = state_interval * (1.0 + jitter_ratio)
                min_delay = max(min_delay, jittered_min)
                max_delay = max(max_delay, jittered_max)
            target_delay = random.uniform(min_delay, max_delay)
            elapsed = (now - last_request_at).total_seconds()
            remaining = target_delay - elapsed
            if remaining > 0:
                self._emit_event(
                    "api_waiting",
                    source_name=source.source_name,
                    fetch_mode=fetch_mode,
                    wait_reason="throttle_window",
                    wait_seconds=round(remaining, 3),
                )
                await asyncio.sleep(remaining)
        self._last_request_at_by_source[source.source_name] = datetime.now(UTC)

    async def _wait_for_state_gate(self, *, source: StyleSourceRegistryEntry, fetch_mode: str) -> None:
        if self.session_factory is None:
            return
        async with self.session_factory() as session:
            state = await self._fetch_state_service.get_or_create(session, source=source)
            if state.mode == "blocked_suspected":
                self._emit_event(
                    "api_access_blocked",
                    source_name=source.source_name,
                    fetch_mode=fetch_mode,
                    wait_reason="blocked_suspected",
                    error_class="blocked_suspected",
                )
                raise RuntimeError(
                    f"Source {source.source_name!r} is in blocked_suspected mode and requires manual review"
                )
            next_allowed_at = state.next_allowed_at
            await session.commit()
        if next_allowed_at is None:
            return
        wait_seconds = (next_allowed_at - datetime.now(UTC)).total_seconds()
        if wait_seconds > 0:
            self._emit_event(
                "api_waiting",
                source_name=source.source_name,
                fetch_mode=fetch_mode,
                wait_reason="source_state_gate",
                wait_seconds=round(wait_seconds, 3),
            )
            await asyncio.sleep(wait_seconds)

    async def _load_state_interval(self, source: StyleSourceRegistryEntry) -> float | None:
        if self.session_factory is None:
            return None
        async with self.session_factory() as session:
            state = await self._fetch_state_service.get_or_create(session, source=source)
            current_min_interval_sec = float(state.current_min_interval_sec)
            await session.commit()
        return current_min_interval_sec if current_min_interval_sec > 0 else None

    async def _handle_retryable_response(
        self,
        source: StyleSourceRegistryEntry,
        response: httpx.Response,
        *,
        attempt: int,
        fetch_mode: str,
        max_attempts: int,
    ) -> None:
        if attempt >= max_attempts:
            return
        retry_after_seconds = self._parse_retry_after(response.headers.get("Retry-After"))
        await self._sleep_with_backoff(
            source,
            attempt=attempt,
            fetch_mode=fetch_mode,
            retry_after_seconds=retry_after_seconds,
        )

    async def _sleep_with_backoff(
        self,
        source: StyleSourceRegistryEntry,
        *,
        attempt: int,
        fetch_mode: str = "api",
        retry_after_seconds: float | None,
    ) -> None:
        if retry_after_seconds is not None and retry_after_seconds > 0:
            delay_seconds = retry_after_seconds
            wait_reason = "retry_after"
        else:
            delay_seconds = source.crawl_policy.retry_backoff_seconds * attempt
            delay_seconds += random.uniform(0.0, max(float(source.crawl_policy.retry_backoff_jitter_seconds), 0.0))
            wait_reason = "retry_backoff"
        self._emit_event(
            "api_waiting",
            source_name=source.source_name,
            fetch_mode=fetch_mode,
            wait_reason=wait_reason,
            wait_seconds=round(delay_seconds, 3),
            attempt=attempt,
        )
        await asyncio.sleep(delay_seconds)

    def _parse_retry_after(self, value: str | None) -> float | None:
        if not value:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            pass
        try:
            parsed = parsedate_to_datetime(stripped)
        except (TypeError, ValueError, IndexError):
            return None
        return max((parsed - datetime.now(parsed.tzinfo or UTC)).total_seconds(), 0.0)

    def _calculate_latency_ms(self, started: float) -> int:
        return max(int((time.perf_counter() - started) * 1000), 0)

    def _build_donor_api_error(
        self,
        *,
        source: StyleSourceRegistryEntry,
        fetch_mode: str,
        request_url: str,
        error: Exception,
    ) -> DonorApiError:
        if isinstance(error, DonorApiError):
            return error
        if isinstance(error, httpx.TimeoutException):
            reason = "request_timeout"
            status_code = None
        elif isinstance(error, (httpx.NetworkError, httpx.RemoteProtocolError)):
            reason = "network_error"
            status_code = None
        elif isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            if status_code == 429:
                reason = "rate_limited"
            elif 500 <= status_code < 600:
                reason = "upstream_server_error"
            elif status_code in {401, 403}:
                reason = "access_denied"
            else:
                reason = "unexpected_http_status"
        else:
            reason = error.__class__.__name__
            status_code = None
        return DonorApiError(
            source_name=source.source_name,
            fetch_mode=fetch_mode,
            request_url=request_url,
            reason=reason,
            status_code=status_code,
            detail=str(error),
        )

    async def _persist_response_log(
        self,
        *,
        source: StyleSourceRegistryEntry,
        response: httpx.Response,
        fetch_mode: str,
        latency_ms: int,
        error_class: str | None,
    ) -> None:
        if self.session_factory is None:
            return
        async with self.session_factory() as session:
            await self._fetch_log_service.persist(
                session,
                source_name=source.source_name,
                fetch_mode=fetch_mode,
                request_method=response.request.method,
                request_url=str(response.request.url),
                response_status=response.status_code,
                response_headers=dict(response.headers),
                response_body=response.content,
                response_content_type=response.headers.get("Content-Type"),
                latency_ms=latency_ms,
                error_class=error_class,
            )
            await session.commit()

    async def _persist_error_log(
        self,
        *,
        source: StyleSourceRegistryEntry,
        request_url: str,
        fetch_mode: str,
        latency_ms: int,
        error: Exception,
    ) -> None:
        if self.session_factory is None:
            return
        response = error.response if isinstance(error, httpx.HTTPStatusError) else None
        request = error.request if isinstance(error, httpx.RequestError | httpx.HTTPStatusError) else None
        async with self.session_factory() as session:
            await self._fetch_log_service.persist(
                session,
                source_name=source.source_name,
                fetch_mode=fetch_mode,
                request_method=request.method if request is not None else "GET",
                request_url=str(request.url) if request is not None else request_url,
                response_status=response.status_code if response is not None else None,
                response_headers=dict(response.headers) if response is not None else None,
                response_body=response.content if response is not None else None,
                response_content_type=response.headers.get("Content-Type") if response is not None else None,
                latency_ms=latency_ms,
                error_class=error.__class__.__name__,
            )
            await session.commit()

    async def _mark_success(self, *, source: StyleSourceRegistryEntry, http_status: int) -> None:
        if self.session_factory is None:
            return
        async with self.session_factory() as session:
            await self._fetch_state_service.mark_success(
                session,
                source=source,
                http_status=http_status,
            )
            await session.commit()

    async def _mark_empty_body(self, *, source: StyleSourceRegistryEntry, http_status: int | None) -> None:
        if self.session_factory is None:
            return
        async with self.session_factory() as session:
            await self._fetch_state_service.mark_empty_body(
                session,
                source=source,
                http_status=http_status,
            )
            await session.commit()

    async def _mark_error(
        self,
        *,
        source: StyleSourceRegistryEntry,
        error: Exception | None = None,
        error_class: str | None = None,
        http_status: int | None = None,
    ) -> None:
        if self.session_factory is None:
            return
        resolved_error_class = error_class or (error.__class__.__name__ if error is not None else "unknown_error")
        resolved_http_status = http_status
        if resolved_http_status is None and isinstance(error, httpx.HTTPStatusError):
            resolved_http_status = error.response.status_code
        if resolved_http_status is None and isinstance(error, DonorApiError):
            resolved_http_status = error.status_code
        async with self.session_factory() as session:
            await self._fetch_state_service.mark_error(
                session,
                source=source,
                error_class=resolved_error_class,
                http_status=resolved_http_status,
            )
            await session.commit()

    def _build_headers(self, *, source: StyleSourceRegistryEntry, accept: str) -> dict[str, str]:
        return {
            "User-Agent": source.crawl_policy.user_agent,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": f"https://{source.source_site}/",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }

class MediaWikiApiFetcher:
    def __init__(self, *, transport: PoliteHTTPTransport) -> None:
        self.transport = transport

    async def fetch_discovery_payload(self, source: StyleSourceRegistryEntry) -> dict[str, object]:
        if not source.api_endpoint_url:
            raise ValueError(
                f"Source {source.source_name!r} does not define api_endpoint_url for MediaWiki API discovery"
            )

        page_titles = source.discovery_page_titles or (_resolve_mediawiki_title_from_url(source.index_url),)
        page_titles = tuple(title for title in page_titles if isinstance(title, str) and title.strip())
        if not page_titles:
            raise ValueError(
                f"Source {source.source_name!r} does not define discovery_page_titles and index_url "
                f"{source.index_url!r} cannot be resolved to MediaWiki page title"
            )

        pages: list[dict[str, object]] = []
        for page_title in page_titles:
            payload = await self.transport.fetch_json(
                source=source,
                url=source.api_endpoint_url,
                params={
                    "action": "parse",
                    "format": "json",
                    "formatversion": "2",
                    "page": page_title,
                    "prop": "text|links|revid",
                },
                fetch_mode="api_discovery_parse",
            )
            parse_node = payload.get("parse")
            if not isinstance(parse_node, dict):
                raise DonorPayloadError(
                    source_name=source.source_name,
                    fetch_mode="api_discovery_parse",
                    request_url=source.api_endpoint_url,
                    reason="missing_parse_object",
                    detail=f"MediaWiki discovery payload for page {page_title!r} does not contain parse object",
                )
            resolved_title = parse_node.get("title")
            if not isinstance(resolved_title, str) or not resolved_title.strip():
                resolved_title = page_title
            raw_html = parse_node.get("text")
            if not isinstance(raw_html, str):
                raw_html = ""
            pages.append(
                {
                    **parse_node,
                    "title": resolved_title,
                    "page_url": _build_mediawiki_page_url(index_url=source.index_url, title=resolved_title),
                    "page_kind": _classify_discovery_page_kind(resolved_title),
                    "pageid": self._coerce_int(parse_node.get("pageid")),
                    "revid": self._coerce_int(parse_node.get("revid")),
                    "text": raw_html,
                }
            )

        return {"pages": pages}

    async def fetch_candidate_remote_states(
        self,
        source: StyleSourceRegistryEntry,
        candidates: tuple[DiscoveredStyleCandidate, ...],
    ) -> tuple[CandidateRemoteState, ...]:
        if not source.api_endpoint_url:
            raise ValueError(
                f"Source {source.source_name!r} does not define api_endpoint_url for MediaWiki API metadata fetch"
            )
        if not candidates:
            return ()

        resolved: dict[str, CandidateRemoteState] = {}
        for chunk in _chunked(candidates, 25):
            payload = await self.transport.fetch_json(
                source=source,
                url=source.api_endpoint_url,
                params={
                    "action": "query",
                    "format": "json",
                    "formatversion": "2",
                    "prop": "revisions",
                    "titles": "|".join(_resolve_mediawiki_page_title(candidate) for candidate in chunk),
                    "rvprop": "ids",
                    "redirects": "1",
                },
                fetch_mode="api_query_revision_ids",
            )
            resolved.update(self._extract_candidate_remote_states(source=source, candidates=chunk, payload=payload))

        return tuple(
            resolved.get(
                candidate.source_url,
                CandidateRemoteState(
                    source_name=source.source_name,
                    source_title=candidate.source_title,
                    source_url=candidate.source_url,
                ),
            )
            for candidate in candidates
        )

    async def fetch_style_page(
        self,
        source: StyleSourceRegistryEntry,
        candidate: DiscoveredStyleCandidate,
    ) -> ScrapedStylePage:
        if not source.api_endpoint_url:
            raise ValueError(
                f"Source {source.source_name!r} does not define api_endpoint_url for MediaWiki API fetching"
            )

        page_title = _resolve_mediawiki_page_title(candidate)
        parse_payload = await self.transport.fetch_json(
            source=source,
            url=source.api_endpoint_url,
            params={
                "action": "parse",
                "format": "json",
                "formatversion": "2",
                "page": page_title,
                "prop": "text|revid",
            },
            fetch_mode="api_parse",
        )
        revision_payload = await self.transport.fetch_json(
            source=source,
            url=source.api_endpoint_url,
            params={
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "revisions",
                "titles": page_title,
                "rvprop": "ids|timestamp|content",
                "rvslots": "main",
            },
            fetch_mode="api_revisions",
        )

        parse_node = parse_payload.get("parse")
        if not isinstance(parse_node, dict):
            raise DonorPayloadError(
                source_name=source.source_name,
                fetch_mode="api_parse",
                request_url=source.api_endpoint_url,
                reason="missing_parse_object",
                detail=f"MediaWiki parse payload for {candidate.source_url!r} does not contain parse object",
            )

        raw_html = parse_node.get("text")
        if not isinstance(raw_html, str) or not raw_html.strip():
            raise DonorPayloadError(
                source_name=source.source_name,
                fetch_mode="api_parse",
                request_url=source.api_endpoint_url,
                reason="empty_parse_html",
                detail=f"MediaWiki parse payload for {candidate.source_url!r} returned empty HTML",
            )

        page_node = self._extract_query_page(revision_payload, candidate)
        raw_wikitext = self._extract_raw_wikitext(page_node)
        page_id = self._coerce_int(parse_node.get("pageid")) or self._coerce_int(page_node.get("pageid"))
        revision_id = self._coerce_int(parse_node.get("revid")) or self._extract_revision_id(page_node)

        source_title = parse_node.get("title")
        if not isinstance(source_title, str) or not source_title.strip():
            source_title = candidate.source_title

        return ScrapedStylePage(
            source_name=source.source_name,
            source_site=source.source_site,
            source_title=source_title,
            source_url=candidate.source_url,
            fetched_at=datetime.now(UTC),
            raw_html=raw_html,
            fetch_mode="mediawiki_action_api",
            page_id=page_id,
            revision_id=revision_id,
            raw_wikitext=raw_wikitext,
        )

    def _extract_query_page(
        self,
        payload: dict[str, object],
        candidate: DiscoveredStyleCandidate,
    ) -> dict[str, object]:
        query = payload.get("query")
        if not isinstance(query, dict):
            raise DonorPayloadError(
                source_name=candidate.source_name,
                fetch_mode="api_revisions",
                request_url=candidate.source_url,
                reason="missing_query_object",
                detail=f"MediaWiki query payload for {candidate.source_url!r} does not contain query object",
            )
        pages = query.get("pages")
        if not isinstance(pages, list) or not pages:
            raise DonorPayloadError(
                source_name=candidate.source_name,
                fetch_mode="api_revisions",
                request_url=candidate.source_url,
                reason="missing_query_pages",
                detail=f"MediaWiki query payload for {candidate.source_url!r} does not contain pages",
            )
        page = pages[0]
        if not isinstance(page, dict):
            raise DonorPayloadError(
                source_name=candidate.source_name,
                fetch_mode="api_revisions",
                request_url=candidate.source_url,
                reason="invalid_query_page_structure",
                detail=f"MediaWiki query payload for {candidate.source_url!r} has invalid page structure",
            )
        return page

    def _extract_raw_wikitext(self, page_node: dict[str, object]) -> str | None:
        revisions = page_node.get("revisions")
        if not isinstance(revisions, list) or not revisions:
            return None
        revision = revisions[0]
        if not isinstance(revision, dict):
            return None
        slots = revision.get("slots")
        if isinstance(slots, dict):
            main_slot = slots.get("main")
            if isinstance(main_slot, dict):
                content = main_slot.get("content")
                if isinstance(content, str):
                    return content
        content = revision.get("content")
        if isinstance(content, str):
            return content
        return None

    def _extract_candidate_remote_states(
        self,
        *,
        source: StyleSourceRegistryEntry,
        candidates: tuple[DiscoveredStyleCandidate, ...],
        payload: dict[str, object],
    ) -> dict[str, CandidateRemoteState]:
        query = payload.get("query")
        if not isinstance(query, dict):
            raise DonorPayloadError(
                source_name=source.source_name,
                fetch_mode="api_query_revision_ids",
                request_url=source.api_endpoint_url or source.index_url,
                reason="missing_query_object",
                detail=f"MediaWiki metadata payload for source {source.source_name!r} does not contain query object",
            )
        pages = query.get("pages")
        if not isinstance(pages, list):
            raise DonorPayloadError(
                source_name=source.source_name,
                fetch_mode="api_query_revision_ids",
                request_url=source.api_endpoint_url or source.index_url,
                reason="missing_query_pages",
                detail=f"MediaWiki metadata payload for source {source.source_name!r} does not contain pages array",
            )

        candidate_by_title_key = {
            _normalize_mediawiki_title_key(_resolve_mediawiki_page_title(candidate)): candidate for candidate in candidates
        }
        resolved: dict[str, CandidateRemoteState] = {}

        for page in pages:
            if not isinstance(page, dict):
                continue
            page_title = page.get("title")
            if not isinstance(page_title, str):
                continue
            candidate = candidate_by_title_key.get(_normalize_mediawiki_title_key(page_title))
            if candidate is None:
                continue
            resolved[candidate.source_url] = CandidateRemoteState(
                source_name=source.source_name,
                source_title=candidate.source_title,
                source_url=candidate.source_url,
                remote_page_id=self._coerce_int(page.get("pageid")),
                remote_revision_id=self._extract_revision_id(page),
            )

        return resolved

    def _extract_revision_id(self, page_node: dict[str, object]) -> int | None:
        revisions = page_node.get("revisions")
        if not isinstance(revisions, list) or not revisions:
            return None
        revision = revisions[0]
        if not isinstance(revision, dict):
            return None
        return self._coerce_int(revision.get("revid"))

    def _coerce_int(self, value: object) -> int | None:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                return int(stripped)
        return None
