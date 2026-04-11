import unittest
from datetime import datetime, timezone

from app.domain.knowledge.entities import KnowledgeQuery
from app.infrastructure.knowledge.repositories.style_catalog_repository import DatabaseStyleCatalogRepository
from app.models import Style, StyleAlias, StyleProfile, StyleRelation, StyleSource, StyleTrait


class FakeScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)

    def scalars(self):
        return FakeScalarRows(self._rows)


class FakeAsyncSession:
    def __init__(self, results):
        self._results = list(results)

    async def execute(self, statement):
        if not self._results:
            raise AssertionError("Unexpected execute call")
        return self._results.pop(0)


class StyleCatalogRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_maps_parser_backed_style_records_to_knowledge_cards(self) -> None:
        ingested_at = datetime(2026, 4, 11, tzinfo=timezone.utc)
        style = Style(
            id=1,
            canonical_name="soft retro prep",
            slug="soft-retro-prep",
            display_name="Soft Retro Prep",
            status="published",
            source_primary_id=11,
            short_definition="Warm prep style.",
            long_summary="A softened collegiate direction with warm neutrals.",
            confidence_score=0.92,
            first_ingested_at=ingested_at,
        )
        profile = StyleProfile(
            style_id=1,
            essence="soft prep",
            fashion_summary="Soft prep with collegiate balance.",
            visual_summary="Warm textured flat lay.",
            historical_context="Draws from classic collegiate dressing.",
            cultural_context="Updated campus heritage.",
            mood_keywords_json=["warm", "polished"],
            color_palette_json=["camel", "cream", "navy"],
            materials_json=["cotton", "tweed"],
            silhouettes_json=["relaxed collegiate layering"],
            garments_json=["oxford shirt", "pleated chinos"],
            footwear_json=["loafers"],
            accessories_json=["belt"],
            hair_makeup_json=[],
            patterns_textures_json=["tweed"],
            seasonality_json=["autumn"],
            occasion_fit_json=["exhibition"],
            negative_constraints_json=["avoid neon"],
            styling_advice_json=["keep it warm and edited"],
            image_prompt_notes_json=["use breathing space between garments"],
        )
        source = StyleSource(
            id=11,
            source_url="https://example.com/soft-retro-prep",
            source_site="example",
            source_title="Soft Retro Prep",
            fetched_at=ingested_at,
            last_seen_at=ingested_at,
            source_hash="hash-1",
            fetch_mode="api",
            remote_page_id=1,
            remote_revision_id=2,
            content_fingerprint="fp-1",
            raw_html="<html></html>",
            raw_wikitext=None,
            raw_text="Soft Retro Prep text",
            raw_sections_json=[],
            raw_links_json=[],
            parser_version="1",
            normalizer_version="1",
        )
        alias = StyleAlias(
            style_id=1,
            alias="retro prep",
            alias_type="alias",
            language="en",
            is_primary_match_hint=True,
        )
        trait = StyleTrait(
            style_id=1,
            trait_type="palette",
            trait_value="camel",
            weight=1.0,
            source_evidence_id=None,
        )
        relation = StyleRelation(
            source_style_id=1,
            target_style_id=2,
            relation_type="adjacent",
            score=0.8,
            reason="nearby style family",
            source_evidence_id=None,
        )
        session = FakeAsyncSession(
            [
                FakeExecuteResult([1]),
                FakeExecuteResult([(style, profile, source)]),
                FakeExecuteResult([alias]),
                FakeExecuteResult([trait]),
                FakeExecuteResult([relation]),
            ]
        )

        cards = await DatabaseStyleCatalogRepository(session).search(
            query=KnowledgeQuery(mode="style_exploration", style_name="retro prep", limit=5)
        )

        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(card.style_id, "soft-retro-prep")
        self.assertEqual(card.source_ref, "https://example.com/soft-retro-prep")
        self.assertIn("retro prep", card.tags)
        self.assertEqual(card.metadata["palette"], ["camel", "cream", "navy"])
        self.assertEqual(card.metadata["hero_garments"], ["oxford shirt", "pleated chinos"])
        self.assertEqual(card.metadata["historical_context"], "Draws from classic collegiate dressing.")
