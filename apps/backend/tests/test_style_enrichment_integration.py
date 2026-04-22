import unittest
from typing import Any

from app.ingestion.styles.style_chatgpt_enrichment_service import (
    DefaultStyleChatGptEnrichmentService,
    StyleEnrichmentValidationError,
    _LoadedStyleEnrichmentSource,
)
from app.integrations.openai_chatgpt import ChatGptStructuredCompletion, OpenAIChatGptResponseError
from app.models import (
    StyleFashionItemFacet,
    StyleImageFacet,
    StyleKnowledgeFacet,
    StyleLlmEnrichment,
    StylePresentationFacet,
    StyleRelationFacet,
    StyleVisualFacet,
)


class _FakeScalarResult:
    def __init__(self, value: Any = None, values: list[Any] | None = None) -> None:
        self.value = value
        self.values = values or []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.values


class _FakeNestedTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _FakeAsyncSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.existing_by_model: dict[type[Any], Any] = {}

    async def execute(self, statement):
        entity = statement.column_descriptions[0].get("entity")
        return _FakeScalarResult(self.existing_by_model.get(entity))

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        return None

    def begin_nested(self):
        return _FakeNestedTransaction()


class _FakeChatGptClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.model = "gpt-test"
        self.payload = payload
        self.calls = 0

    async def complete_json(self, *, system_prompt: str, user_prompt: str):
        self.calls += 1
        return ChatGptStructuredCompletion(
            payload=self.payload,
            provider=self.model,
            raw_content='{"ok": true}',
        )


class _FakeInvalidJsonClient:
    def __init__(self) -> None:
        self.model = "gpt-test"
        self.calls = 0

    async def complete_json(self, *, system_prompt: str, user_prompt: str):
        self.calls += 1
        raise OpenAIChatGptResponseError(
            "OpenAI enrichment response was not valid JSON",
            raw_content="{broken",
        )


class _IntegrationStyleEnrichmentService(DefaultStyleChatGptEnrichmentService):
    async def _load_source_material(self, *, style_id: int) -> _LoadedStyleEnrichmentSource:
        return _LoadedStyleEnrichmentSource(
            style_id=style_id,
            style_slug="soft-academia",
            style_name="Soft Academia",
            source_title="Soft Academia",
            source_url="https://example.test/wiki/Soft_Academia",
            source_page_id=55,
            cleaned_source_text="Soft Academia blends academic codes with gentle texture.",
            evidence_items=["Layered neutrals and soft lighting are recurring cues."],
        )


def _valid_enrichment_payload() -> dict[str, Any]:
    return {
        "knowledge": {
            "core_definition": "Gentle academic styling.",
            "core_style_logic": ["soft tailoring"],
            "styling_rules": ["layer knits over shirts"],
            "casual_adaptations": ["relaxed cardigan"],
            "statement_pieces": ["satchel"],
            "status_markers": ["bookish polish"],
            "overlap_context": ["light academia"],
            "historical_notes": ["campus nostalgia"],
            "negative_guidance": ["avoid harsh neon"],
        },
        "visual_language": {
            "palette": ["cream", "warm brown"],
            "lighting_mood": ["soft daylight"],
            "photo_treatment": ["matte editorial"],
            "visual_motifs": ["books"],
            "patterns_textures": ["wool"],
            "platform_visual_cues": ["flat lay"],
        },
        "fashion_items": {
            "tops": ["oxford shirt"],
            "bottoms": ["pleated skirt"],
            "shoes": ["loafers"],
            "accessories": ["satchel"],
            "hair_makeup": ["soft waves"],
            "signature_details": ["ribbon"],
        },
        "image_prompt_atoms": {
            "hero_garments": ["cream cardigan"],
            "secondary_garments": ["cotton blouse"],
            "core_accessories": ["leather satchel"],
            "props": ["open book"],
            "materials": ["wool", "cotton"],
            "composition_cues": ["tabletop flat lay"],
            "negative_constraints": ["no neon"],
            "visual_motifs": ["library desk"],
            "lighting_mood": ["window light"],
            "photo_treatment": ["soft grain"],
        },
        "relations": {
            "related_styles": ["Light Academia"],
            "overlap_styles": ["Classic Academia"],
            "preceded_by": ["Academia"],
            "succeeded_by": ["Soft Academia Revival"],
            "brands": ["vintage bookstore"],
            "platforms": ["Pinterest"],
            "origin_regions": ["UK"],
            "era": ["2010s"],
        },
        "presentation": {
            "short_explanation": "A softer academic mood.",
            "one_sentence_description": "Soft Academia relaxes collegiate polish.",
            "what_makes_it_distinct": ["gentle palette", "quiet study mood"],
        },
    }


def _added_one(session: _FakeAsyncSession, model: type[Any]):
    matches = [item for item in session.added if isinstance(item, model)]
    assert len(matches) == 1
    return matches[0]


class StyleEnrichmentIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_enrichment_writes_all_facet_tables_and_success_log(self) -> None:
        session = _FakeAsyncSession()
        client = _FakeChatGptClient(_valid_enrichment_payload())
        events: list[tuple[str, dict[str, Any]]] = []
        service = _IntegrationStyleEnrichmentService(
            session=session,
            client=client,
            progress_reporter=lambda event, payload: events.append((event, payload)),
        )

        result = await service.enrich_style(101)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.source_page_id, 55)
        self.assertEqual(client.calls, 1)
        self.assertEqual(_added_one(session, StyleKnowledgeFacet).core_definition, "Gentle academic styling.")
        self.assertEqual(_added_one(session, StyleVisualFacet).palette_json, ["cream", "warm brown"])
        self.assertEqual(_added_one(session, StyleFashionItemFacet).tops_json, ["oxford shirt"])
        self.assertEqual(_added_one(session, StyleImageFacet).hero_garments_json, ["cream cardigan"])
        self.assertEqual(_added_one(session, StyleRelationFacet).related_styles_json, ["Light Academia"])
        self.assertEqual(_added_one(session, StylePresentationFacet).short_explanation, "A softer academic mood.")
        log = _added_one(session, StyleLlmEnrichment)
        self.assertEqual(log.status, "succeeded")
        self.assertEqual(log.source_page_id, 55)
        self.assertIn("style_enrichment_run_finished", [event for event, _payload in events])

    async def test_invalid_json_writes_failed_validation_log_without_facet_rows(self) -> None:
        session = _FakeAsyncSession()
        client = _FakeInvalidJsonClient()
        service = _IntegrationStyleEnrichmentService(session=session, client=client)

        with self.assertRaises(StyleEnrichmentValidationError):
            await service.enrich_style(101)

        self.assertEqual(client.calls, service.MAX_VALIDATION_ATTEMPTS)
        facet_rows = [
            item
            for item in session.added
            if isinstance(
                item,
                (
                    StyleKnowledgeFacet,
                    StyleVisualFacet,
                    StyleFashionItemFacet,
                    StyleImageFacet,
                    StyleRelationFacet,
                    StylePresentationFacet,
                ),
            )
        ]
        self.assertEqual(facet_rows, [])
        log = _added_one(session, StyleLlmEnrichment)
        self.assertEqual(log.status, "failed_validation")
        self.assertEqual(log.source_page_id, 55)


if __name__ == "__main__":
    unittest.main()
