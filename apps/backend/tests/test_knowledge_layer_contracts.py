import unittest

from app.domain.knowledge.entities import (
    KnowledgeCard,
    KnowledgeProviderConfig,
    KnowledgeQuery,
    KnowledgeRuntimeFlags,
)
from app.domain.knowledge.enums import KnowledgeType


class KnowledgeLayerContractTests(unittest.TestCase):
    def test_knowledge_query_supports_richer_runtime_fields_with_legacy_compatibility(self) -> None:
        query = KnowledgeQuery(
            mode="style_exploration",
            style_id="dark-academia",
            style_ids=["dark-academia", 42],
            style_families=["academic", "vintage"],
            eras=["1930s", "1990s"],
            retrieval_profile="visual_heavy",
            need_visual_knowledge=True,
            need_historical_knowledge=True,
            need_styling_rules=True,
            need_color_poetics=True,
            message="legacy message",
            user_request="Need a cinematic dark academia direction",
        )

        self.assertEqual(query.resolved_style_ids(), ["dark-academia", "42"])
        self.assertEqual(query.resolved_user_request(), "Need a cinematic dark academia direction")
        self.assertEqual(query.retrieval_profile, "visual_heavy")
        self.assertTrue(query.need_visual_knowledge)
        self.assertTrue(query.need_historical_knowledge)
        self.assertTrue(query.need_styling_rules)
        self.assertTrue(query.need_color_poetics)

    def test_knowledge_query_falls_back_to_legacy_message_field(self) -> None:
        query = KnowledgeQuery(mode="general_advice", message="legacy prompt only")
        self.assertEqual(query.resolved_user_request(), "legacy prompt only")

    def test_knowledge_card_reference_exposes_provider_and_style_runtime_fields(self) -> None:
        card = KnowledgeCard(
            id="style_visual:dark-academia",
            knowledge_type=KnowledgeType.STYLE_VISUAL_LANGUAGE,
            provider_code="style_ingestion",
            provider_priority=10,
            title="Dark Academia Visual Language",
            summary="Muted library palette and low-key lighting.",
            style_id="dark-academia",
            style_family="academic",
            era_code="1930s",
            tone_role="editorial",
            document_ref="doc-1",
            chunk_ref="chunk-2",
        )

        reference = card.reference()
        self.assertEqual(reference["provider_code"], "style_ingestion")
        self.assertEqual(reference["style_family"], "academic")
        self.assertEqual(reference["era_code"], "1930s")

    def test_knowledge_provider_config_tracks_runtime_and_ingestion_enablement(self) -> None:
        config = KnowledgeProviderConfig(
            code="style_ingestion",
            name="Style Ingestion",
            provider_type="distilled_style",
            is_enabled=True,
            is_runtime_enabled=True,
            is_ingestion_enabled=False,
            priority=5,
            runtime_roles=["reasoning", "voice"],
        )

        self.assertTrue(config.is_available_for_runtime())
        self.assertFalse(config.is_available_for_ingestion())
        self.assertEqual(config.runtime_roles, ["reasoning", "voice"])

    def test_knowledge_runtime_flags_gate_future_provider_codes_and_roles(self) -> None:
        flags = KnowledgeRuntimeFlags(
            malevich_enabled=False,
            fashion_historian_enabled=True,
            stylist_enabled=False,
            use_editorial_knowledge=False,
            use_historical_context=True,
            use_color_poetics=False,
        )

        self.assertFalse(
            flags.allows_provider(
                KnowledgeProviderConfig(
                    code="malevich",
                    name="Malevich",
                    runtime_roles=["color_poetics"],
                )
            )
        )
        self.assertTrue(
            flags.allows_provider(
                KnowledgeProviderConfig(
                    code="fashion_historian",
                    name="Historian",
                    runtime_roles=["historical_context"],
                )
            )
        )
        self.assertFalse(
            flags.allows_provider(
                KnowledgeProviderConfig(
                    code="stylist_editorial",
                    name="Stylist",
                    runtime_roles=["editorial"],
                )
            )
        )
