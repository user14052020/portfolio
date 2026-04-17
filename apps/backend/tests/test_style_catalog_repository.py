import unittest
from datetime import datetime, timezone

from app.domain.knowledge.entities import KnowledgeQuery
from app.infrastructure.knowledge.repositories.style_catalog_repository import DatabaseStyleCatalogRepository
from app.models import (
    Style,
    StyleAlias,
    StyleFashionItemFacet,
    StyleImageFacet,
    StyleKnowledgeFacet,
    StylePresentationFacet,
    StyleProfile,
    StyleRelation,
    StyleRelationFacet,
    StyleSource,
    StyleTrait,
    StyleVisualFacet,
)


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
        knowledge_facet = StyleKnowledgeFacet(
            style_id=1,
            facet_version="2026-04",
            core_definition="A warmer and more relaxed collegiate style.",
            core_style_logic_json=["Blend collegiate structure with softened warmth."],
            styling_rules_json=["Keep prep elements edited and breathable."],
            casual_adaptations_json=["Use softer knits instead of stiff layers."],
            statement_pieces_json=["camel blazer"],
            status_markers_json=["heritage loafers"],
            overlap_context_json=["bridges prep and retro casual dressing"],
            historical_notes_json=["References collegiate heritage with a softer, modern filter."],
            negative_guidance_json=["Avoid neon accents."],
        )
        visual_facet = StyleVisualFacet(
            style_id=1,
            facet_version="2026-04",
            palette_json=["camel", "cream", "navy"],
            lighting_mood_json=["soft daylight"],
            photo_treatment_json=["editorial grain"],
            visual_motifs_json=["relaxed layering"],
            patterns_textures_json=["tweed", "oxford cotton"],
            platform_visual_cues_json=["quiet luxury editorial"],
        )
        fashion_facet = StyleFashionItemFacet(
            style_id=1,
            facet_version="2026-04",
            tops_json=["oxford shirt"],
            bottoms_json=["pleated chinos"],
            shoes_json=["loafers"],
            accessories_json=["belt"],
            hair_makeup_json=[],
            signature_details_json=["softly structured blazer"],
        )
        image_facet = StyleImageFacet(
            style_id=1,
            facet_version="2026-04",
            hero_garments_json=["camel blazer", "oxford shirt"],
            secondary_garments_json=["pleated chinos"],
            core_accessories_json=["belt"],
            props_json=["folded magazine"],
            materials_json=["cotton", "tweed"],
            composition_cues_json=["leave breathing room between garments"],
            negative_constraints_json=["avoid neon"],
            visual_motifs_json=["relaxed layering"],
            lighting_mood_json=["soft daylight"],
            photo_treatment_json=["editorial grain"],
        )
        relation_facet = StyleRelationFacet(
            style_id=1,
            facet_version="2026-04",
            related_styles_json=["ivy style"],
            overlap_styles_json=["retro prep"],
            preceded_by_json=["classic prep"],
            succeeded_by_json=["soft academia"],
            brands_json=["Ralph Lauren"],
            platforms_json=["editorial lookbook"],
            origin_regions_json=["US campus style"],
            era_json=["1980s revival"],
        )
        presentation_facet = StylePresentationFacet(
            style_id=1,
            facet_version="2026-04",
            short_explanation="Soft Retro Prep reframes collegiate dressing through warmer colors and softer structure.",
            one_sentence_description="A softened collegiate direction with warm neutrals and relaxed polish.",
            what_makes_it_distinct_json=["Warm prep palette", "Relaxed but polished layering"],
        )
        session = FakeAsyncSession(
            [
                FakeExecuteResult([1]),
                FakeExecuteResult([(style, profile, source)]),
                FakeExecuteResult([alias]),
                FakeExecuteResult([trait]),
                FakeExecuteResult([relation]),
                FakeExecuteResult([knowledge_facet]),
                FakeExecuteResult([visual_facet]),
                FakeExecuteResult([fashion_facet]),
                FakeExecuteResult([image_facet]),
                FakeExecuteResult([relation_facet]),
                FakeExecuteResult([presentation_facet]),
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
        self.assertEqual(
            card.summary,
            "Soft Retro Prep reframes collegiate dressing through warmer colors and softer structure.",
        )
        self.assertEqual(card.metadata["palette"], ["camel", "cream", "navy"])
        self.assertEqual(card.metadata["hero_garments"], ["camel blazer", "oxford shirt"])
        self.assertEqual(card.metadata["core_style_logic"], ["Blend collegiate structure with softened warmth."])
        self.assertEqual(
            card.metadata["historical_context"],
            "References collegiate heritage with a softer, modern filter.; Draws from classic collegiate dressing.",
        )
        self.assertTrue(card.metadata["has_enriched_facets"])
