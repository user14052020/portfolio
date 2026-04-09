from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.ingestion.styles.contracts import DiscoveredStyleCandidate, ScrapedStylePage, StyleScraper, StyleSourceRegistryEntry


class HTTPStyleScraper(StyleScraper):
    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._last_request_at_by_source: dict[str, datetime] = {}
        self._locks_by_source: dict[str, asyncio.Lock] = {}
        self._robots_parser_by_source: dict[str, RobotFileParser | None] = {}
        self._robots_crawl_delay_by_source: dict[str, float | None] = {}

    async def fetch_index_html(self, source: StyleSourceRegistryEntry) -> str:
        response = await self._send_get(source=source, url=source.index_url)
        return response.text

    async def fetch_style_page(
        self,
        source: StyleSourceRegistryEntry,
        candidate: DiscoveredStyleCandidate,
    ) -> ScrapedStylePage:
        response = await self._send_get(source=source, url=candidate.source_url)
        return ScrapedStylePage(
            source_name=source.source_name,
            source_site=source.source_site,
            source_title=candidate.source_title,
            source_url=candidate.source_url,
            fetched_at=datetime.now(UTC),
            raw_html=response.text,
        )

    async def _send_get(self, *, source: StyleSourceRegistryEntry, url: str) -> httpx.Response:
        lock = self._locks_by_source.setdefault(source.source_name, asyncio.Lock())
        async with lock:
            last_error: Exception | None = None
            max_attempts = max(source.crawl_policy.max_retries, 1)

            for attempt in range(1, max_attempts + 1):
                await self._ensure_allowed_by_robots(source=source, url=url)
                await self._wait_for_turn(source)
                try:
                    async with httpx.AsyncClient(
                        timeout=self.timeout_seconds,
                        follow_redirects=True,
                        headers=self._build_headers(source=source, accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
                    ) as client:
                        response = await client.get(url)
                    if response.status_code == 429 or 500 <= response.status_code < 600:
                        await self._handle_retryable_response(source, response, attempt=attempt, max_attempts=max_attempts)
                        last_error = httpx.HTTPStatusError(
                            f"Retryable HTTP status: {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                        continue
                    response.raise_for_status()
                    return response
                except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError, httpx.HTTPStatusError) as exc:
                    last_error = exc
                    if attempt >= max_attempts:
                        break
                    await self._sleep_with_backoff(source, attempt=attempt, retry_after_seconds=None)

            assert last_error is not None
            raise last_error

    async def _wait_for_turn(self, source: StyleSourceRegistryEntry) -> None:
        now = datetime.now(UTC)
        last_request_at = self._last_request_at_by_source.get(source.source_name)
        if last_request_at is not None:
            crawl_delay = self._robots_crawl_delay_by_source.get(source.source_name)
            min_delay = source.crawl_policy.min_delay_seconds
            max_delay = source.crawl_policy.max_delay_seconds
            if crawl_delay is not None and crawl_delay > 0:
                min_delay = max(min_delay, crawl_delay)
                max_delay = max(max_delay, crawl_delay)
            target_delay = random.uniform(
                min_delay,
                max_delay,
            )
            elapsed = (now - last_request_at).total_seconds()
            remaining = target_delay - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
        self._last_request_at_by_source[source.source_name] = datetime.now(UTC)

    async def _handle_retryable_response(
        self,
        source: StyleSourceRegistryEntry,
        response: httpx.Response,
        *,
        attempt: int,
        max_attempts: int,
    ) -> None:
        if attempt >= max_attempts:
            return
        retry_after_seconds = self._parse_retry_after(response.headers.get("Retry-After"))
        await self._sleep_with_backoff(source, attempt=attempt, retry_after_seconds=retry_after_seconds)

    async def _sleep_with_backoff(
        self,
        source: StyleSourceRegistryEntry,
        *,
        attempt: int,
        retry_after_seconds: float | None,
    ) -> None:
        if retry_after_seconds is not None and retry_after_seconds > 0:
            delay_seconds = retry_after_seconds
        else:
            delay_seconds = source.crawl_policy.retry_backoff_seconds * attempt
            delay_seconds += random.uniform(0.0, 1.0)
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

    async def _ensure_allowed_by_robots(self, *, source: StyleSourceRegistryEntry, url: str) -> None:
        if not source.crawl_policy.respect_robots_txt:
            return

        parser = self._robots_parser_by_source.get(source.source_name)
        if parser is None and source.source_name not in self._robots_parser_by_source:
            parser = await self._load_robots_parser(source)
            self._robots_parser_by_source[source.source_name] = parser

        if parser is None:
            return

        if not parser.can_fetch(source.crawl_policy.user_agent, url):
            raise PermissionError(
                f"Robots policy forbids fetching {url!r} for source {source.source_name!r}"
            )

    async def _load_robots_parser(self, source: StyleSourceRegistryEntry) -> RobotFileParser | None:
        robots_url = source.crawl_policy.robots_txt_url or self._build_robots_url(source)
        last_error: Exception | None = None
        max_attempts = max(source.crawl_policy.max_retries, 1)

        for attempt in range(1, max_attempts + 1):
            await self._wait_for_turn(source)
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout_seconds,
                    follow_redirects=True,
                    headers=self._build_headers(source=source, accept="text/plain,text/html,*/*;q=0.8"),
                ) as client:
                    response = await client.get(robots_url)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                last_error = exc
                if attempt >= max_attempts:
                    return None
                await self._sleep_with_backoff(source, attempt=attempt, retry_after_seconds=None)
                continue

            if response.status_code == 404:
                return None

            if response.status_code in {429} or 500 <= response.status_code < 600:
                last_error = httpx.HTTPStatusError(
                    f"Retryable robots HTTP status: {response.status_code}",
                    request=response.request,
                    response=response,
                )
                if attempt >= max_attempts:
                    break
                retry_after_seconds = self._parse_retry_after(response.headers.get("Retry-After"))
                await self._sleep_with_backoff(
                    source,
                    attempt=attempt,
                    retry_after_seconds=retry_after_seconds,
                )
                continue

            if response.status_code in {401, 403}:
                raise PermissionError(
                    f"Robots policy is unavailable for source {source.source_name!r}: "
                    f"HTTP {response.status_code} at {robots_url}"
                )

            response.raise_for_status()

            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.text.splitlines())
            self._robots_crawl_delay_by_source[source.source_name] = parser.crawl_delay(
                source.crawl_policy.user_agent
            )
            return parser

        if isinstance(last_error, httpx.HTTPStatusError):
            raise last_error
        return None

    def _build_robots_url(self, source: StyleSourceRegistryEntry) -> str:
        parsed = urlparse(source.index_url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def _build_headers(self, *, source: StyleSourceRegistryEntry, accept: str) -> dict[str, str]:
        return {
            "User-Agent": source.crawl_policy.user_agent,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": f"https://{source.source_site}/",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }
