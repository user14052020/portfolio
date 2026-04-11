import unittest

from app.ingestion.styles.contracts import SourceCrawlPolicy, StyleSourceRegistryEntry
from app.ingestion.styles.style_fetchers import PoliteHTTPTransport
from app.ingestion.styles.style_source_registry import AestheticsWikiSourceRegistry


class GuardedTransport(PoliteHTTPTransport):
    def __init__(self) -> None:
        super().__init__()
        self.robots_loader_calls = 0

    async def _load_robots_parser(self, source):  # type: ignore[override]
        self.robots_loader_calls += 1
        raise AssertionError("robots loader must not run for api-only source")


class StyleIngestionTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_only_source_skips_robots_loading(self) -> None:
        transport = GuardedTransport()
        source = StyleSourceRegistryEntry(
            source_name="api_only_source",
            source_site="example.test",
            index_url="https://example.test/wiki/List_of_Styles",
            discovery_page_titles=("List of Styles",),
            allowed_domains=("example.test",),
            parser_version="0.1.0",
            normalizer_version="0.1.0",
            crawl_policy=SourceCrawlPolicy(
                user_agent="TestBot/1.0",
                respect_robots_txt=False,
                robots_txt_url=None,
            ),
            api_endpoint_url="https://example.test/api.php",
        )

        await transport._ensure_allowed_by_robots(
            source=source,
            url="https://example.test/api.php?action=parse",
        )

        self.assertEqual(transport.robots_loader_calls, 0)

    def test_aesthetics_wiki_registry_is_configured_as_api_only_without_robots_dependency(self) -> None:
        registry = AestheticsWikiSourceRegistry()
        source = registry.get_source("aesthetics_wiki")

        self.assertFalse(source.crawl_policy.respect_robots_txt)
        self.assertIsNone(source.crawl_policy.robots_txt_url)
        self.assertEqual(source.discovery_fetch_mode, "mediawiki_action_api")
        self.assertEqual(source.detail_fetch_mode, "mediawiki_action_api")

