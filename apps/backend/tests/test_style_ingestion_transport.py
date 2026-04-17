import unittest
from unittest.mock import patch

import httpx

from app.ingestion.styles.contracts import SourceCrawlPolicy, StyleSourceRegistryEntry
from app.ingestion.styles.errors import DonorApiError, DonorPayloadError
from app.ingestion.styles.style_fetchers import MediaWikiApiFetcher, PoliteHTTPTransport
from app.ingestion.styles.style_source_registry import AestheticsWikiSourceRegistry


class _FakeAsyncClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str, params: dict[str, str] | None = None) -> httpx.Response:
        return self._response


class _FakeTransport:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[dict[str, object]] = []

    async def fetch_json(self, **kwargs) -> dict[str, object]:
        self.calls.append(dict(kwargs))
        return self.payload


def _build_source(*, max_retries: int = 1) -> StyleSourceRegistryEntry:
    return StyleSourceRegistryEntry(
        source_name="api_only_source",
        source_site="example.test",
        index_url="https://example.test/wiki/List_of_Styles",
        discovery_page_titles=("List of Styles",),
        allowed_domains=("example.test",),
        parser_version="0.1.0",
        normalizer_version="0.1.0",
        crawl_policy=SourceCrawlPolicy(
            user_agent="TestBot/1.0",
            min_delay_seconds=0.0,
            max_delay_seconds=0.0,
            max_retries=max_retries,
            retry_backoff_seconds=0.0,
        ),
        api_endpoint_url="https://example.test/api.php",
    )


class StyleIngestionTransportTests(unittest.IsolatedAsyncioTestCase):
    def test_transport_no_longer_exposes_robots_runtime_hooks(self) -> None:
        transport = PoliteHTTPTransport()

        self.assertFalse(hasattr(transport, "_ensure_allowed_by_robots"))
        self.assertFalse(hasattr(transport, "_load_robots_parser"))
        self.assertFalse(hasattr(transport, "_build_robots_url"))

    def test_aesthetics_wiki_registry_is_api_only_without_robots_contract(self) -> None:
        registry = AestheticsWikiSourceRegistry()
        source = registry.get_source("aesthetics_wiki")

        self.assertFalse(hasattr(source.crawl_policy, "respect_robots_txt"))
        self.assertFalse(hasattr(source.crawl_policy, "robots_txt_url"))
        self.assertEqual(source.discovery_fetch_mode, "mediawiki_action_api")
        self.assertEqual(source.detail_fetch_mode, "mediawiki_action_api")

    async def test_discovery_fetcher_uses_donor_api_only_without_robots(self) -> None:
        source = _build_source()
        transport = _FakeTransport(
            {
                "parse": {
                    "title": "List of Styles",
                    "text": "<div><a href=\"/wiki/Test_Style\">Test Style</a></div>",
                    "pageid": 10,
                    "revid": 20,
                }
            }
        )
        fetcher = MediaWikiApiFetcher(transport=transport)

        payload = await fetcher.fetch_discovery_payload(source)

        self.assertEqual(len(payload["pages"]), 1)
        self.assertEqual(transport.calls[0]["url"], "https://example.test/api.php")
        self.assertEqual(transport.calls[0]["fetch_mode"], "api_discovery_parse")
        self.assertNotIn("robots.txt", transport.calls[0]["url"])

    async def test_transport_emits_structured_api_events_on_success(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        source = _build_source()
        request = httpx.Request("GET", "https://example.test/api.php?action=parse")
        response = httpx.Response(
            200,
            request=request,
            json={"parse": {"title": "Test"}},
            headers={"Content-Type": "application/json"},
        )

        with patch("app.ingestion.styles.style_fetchers.httpx.AsyncClient", return_value=_FakeAsyncClient(response)):
            transport = PoliteHTTPTransport(event_reporter=lambda event, payload: events.append((event, payload)))
            payload = await transport.fetch_json(
                source=source,
                url="https://example.test/api.php",
                params={"action": "parse"},
                fetch_mode="api_parse",
            )

        self.assertEqual(payload["parse"]["title"], "Test")
        self.assertEqual(events[0][0], "api_request_started")
        self.assertEqual(events[-1][0], "api_request_succeeded")
        self.assertEqual(events[-1][1]["response_status"], 200)

    async def test_transport_raises_domain_error_for_donor_api_status_failure(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        source = _build_source(max_retries=1)
        request = httpx.Request("GET", "https://example.test/api.php?action=parse")
        response = httpx.Response(
            500,
            request=request,
            json={"error": "upstream"},
            headers={"Content-Type": "application/json"},
        )

        with patch("app.ingestion.styles.style_fetchers.httpx.AsyncClient", return_value=_FakeAsyncClient(response)):
            transport = PoliteHTTPTransport(event_reporter=lambda event, payload: events.append((event, payload)))
            with self.assertRaises(DonorApiError) as raised:
                await transport.fetch_json(
                    source=source,
                    url="https://example.test/api.php",
                    params={"action": "parse"},
                    fetch_mode="api_parse",
                )

        self.assertEqual(raised.exception.reason, "upstream_server_error")
        self.assertEqual(raised.exception.fetch_mode, "api_parse")
        self.assertEqual(raised.exception.status_code, 500)
        event_names = [name for name, _payload in events]
        self.assertIn("api_request_started", event_names)
        self.assertIn("api_request_failed", event_names)
        self.assertNotIn("api_request_succeeded", event_names)

    async def test_transport_raises_domain_error_for_invalid_donor_payload(self) -> None:
        events: list[tuple[str, dict[str, object]]] = []
        source = _build_source()
        request = httpx.Request("GET", "https://example.test/api.php?action=parse")
        response = httpx.Response(
            200,
            request=request,
            json=["not", "an", "object"],
            headers={"Content-Type": "application/json"},
        )

        with patch("app.ingestion.styles.style_fetchers.httpx.AsyncClient", return_value=_FakeAsyncClient(response)):
            transport = PoliteHTTPTransport(event_reporter=lambda event, payload: events.append((event, payload)))
            with self.assertRaises(DonorPayloadError) as raised:
                await transport.fetch_json(
                    source=source,
                    url="https://example.test/api.php",
                    params={"action": "parse"},
                    fetch_mode="api_parse",
                )

        self.assertEqual(raised.exception.reason, "invalid_json_object")
        self.assertEqual(raised.exception.fetch_mode, "api_parse")
        event_names = [name for name, _payload in events]
        self.assertIn("api_request_started", event_names)
        self.assertIn("api_request_failed", event_names)
        self.assertNotIn("api_request_succeeded", event_names)
