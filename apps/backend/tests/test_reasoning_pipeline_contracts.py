from pathlib import Path
import unittest

from app.application.prompt_building.services.fashion_reasoning_service import (
    FashionReasoningInput as PromptFashionReasoningInput,
)
from app.application.reasoning import (
    DefaultFashionBriefBuilder,
    DefaultProfileClarificationPolicy,
    DefaultFashionReasoningContextAssembler,
    DefaultFashionReasoningPipeline,
    DefaultFashionReasoner,
    DefaultProfileStyleAlignmentService,
    DefaultReasoningOutputMapper,
    DefaultRetrievalProfileSelector,
    DefaultVoiceLayerComposer,
    ProfileAlignedFashionReasoningContextAssembler,
    FashionBriefBuilder,
    FashionReasoner,
    FashionReasoningContextAssembler,
    FashionReasoningPipeline,
    ProfileStyleAlignmentService,
    ReasoningOutputMapper,
)
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery, KnowledgeRuntimeFlags
from app.domain.knowledge.enums import KnowledgeType
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.reasoning import (
    FashionReasoningInput,
    FashionReasoningOutput,
    FashionReasoningPresentationPayload,
    GenerationHandoffPayload,
    ImageCtaCandidate,
    KnowledgeContext,
    PresentationProfile,
    ProfileClarificationDecision,
    ProfileAlignedStyleFacetBundle,
    ProfileContext,
    ProfileContextSnapshot,
    ReasoningMetadata,
    ReasoningRetrievalQuery,
    SessionStateSnapshot,
    StyleAdviceFacet,
    StyleFacetBundle,
    StyleImageFacet,
    StyleKnowledgeCard,
    StyleRelationFacet,
    StyleSemanticFragmentSummary,
    StyledAnswer,
    StyleVisualLanguageFacet,
    UsedStyleReference,
    VoiceContext,
    VoiceLayerReasoningPayload,
    VoiceToneDecision,
)
from app.domain.routing.entities.routing_decision import RoutingDecision
from app.domain.routing.enums.routing_mode import RoutingMode
from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints
from app.infrastructure.reasoning import StyleDistilledReasoningProvider


class ReasoningPipelineContractsTests(unittest.TestCase):
    def test_voice_contracts_capture_context_answer_and_tone_decision(self) -> None:
        context = VoiceContext(
            mode="style_exploration",
            response_type="text_with_visual_offer",
            desired_depth="deep",
            should_be_brief=False,
            can_use_historical_layer=True,
            can_use_color_poetics=True,
            can_offer_visual_cta=True,
            profile_context_present=True,
            knowledge_density="high",
        )
        styled_answer = StyledAnswer(
            text="I would keep the line long and quiet, then let the shine sit in the accessories.",
            tone_profile="smart_stylist_with_controlled_editorial_depth",
            voice_layers_used=["stylist", "historian", "color_poetics"],
            includes_historical_note=True,
            includes_color_poetics=True,
            cta_text="If helpful, I can turn this into a flat lay reference.",
            brevity_level="deep",
            observability={"voice_cta_style": "editorial_soft"},
        )
        tone_decision = VoiceToneDecision(
            base_tone="smart_stylist",
            use_historian_layer=True,
            use_color_poetics_layer=True,
            brevity_level="deep",
            expressive_density="rich_but_controlled",
            cta_style="editorial_soft",
        )

        self.assertEqual(context.mode, "style_exploration")
        self.assertEqual(context.response_type, "text_with_visual_offer")
        self.assertEqual(context.desired_depth, "deep")
        self.assertTrue(context.can_use_historical_layer)
        self.assertTrue(context.can_use_color_poetics)
        self.assertEqual(context.knowledge_density, "high")
        self.assertEqual(styled_answer.voice_layers_used, ["stylist", "historian", "color_poetics"])
        self.assertTrue(styled_answer.includes_historical_note)
        self.assertTrue(styled_answer.includes_color_poetics)
        self.assertEqual(styled_answer.brevity_level, "deep")
        self.assertEqual(styled_answer.observability["voice_cta_style"], "editorial_soft")
        self.assertEqual(tone_decision.base_tone, "smart_stylist")
        self.assertTrue(tone_decision.use_historian_layer)
        self.assertTrue(tone_decision.use_color_poetics_layer)
        self.assertEqual(tone_decision.cta_style, "editorial_soft")

    def test_profile_context_snapshot_supports_typed_and_legacy_payloads(self) -> None:
        typed_context = ProfileContext(
            presentation_profile=PresentationProfile.ANDROGYNOUS,
            fit_preferences=["relaxed"],
            silhouette_preferences=["structured"],
            comfort_preferences=["balanced"],
            preferred_items=["wide-leg trousers"],
            avoided_items=["heels"],
        )
        typed_snapshot = typed_context.snapshot(
            legacy_values={"height_cm": 175},
        )
        legacy_snapshot = ProfileContextSnapshot(
            values={
                "presentation_profile": "feminine",
                "fit": "fitted",
                "silhouette_preferences": ["soft", "soft"],
                "preferred_items": ["skirts", "skirts"],
                "avoid_items": "heels",
                "height_cm": 168,
            },
            present=True,
        )

        self.assertTrue(typed_snapshot.present)
        self.assertEqual(typed_snapshot.presentation_profile, "androgynous")
        self.assertEqual(typed_snapshot.fit_preferences, ("relaxed",))
        self.assertEqual(typed_snapshot.legacy_values, {"height_cm": 175})
        self.assertEqual(typed_snapshot.values["preferred_items"], ["wide-leg trousers"])
        self.assertEqual(
            typed_snapshot.as_profile_context().presentation_profile,
            PresentationProfile.ANDROGYNOUS,
        )
        self.assertTrue(legacy_snapshot.present)
        self.assertEqual(legacy_snapshot.presentation_profile, "feminine")
        self.assertEqual(legacy_snapshot.fit_preferences, ("fitted",))
        self.assertEqual(legacy_snapshot.silhouette_preferences, ("soft",))
        self.assertEqual(legacy_snapshot.preferred_items, ("skirts",))
        self.assertEqual(legacy_snapshot.avoided_items, ("heels",))
        self.assertEqual(legacy_snapshot.values["height_cm"], 168)

    def test_profile_aligned_style_facet_bundle_supports_legacy_and_explicit_shapes(self) -> None:
        advice_facet = StyleAdviceFacet(style_id=12, core_style_logic=["structured contrast"])
        image_facet = StyleImageFacet(style_id=12, hero_garments=["tailored vest"])
        visual_facet = StyleVisualLanguageFacet(style_id=12, palette=["ink", "bone"])
        relation_facet = StyleRelationFacet(style_id=12, related_styles=["minimal tailoring"])
        bundle = StyleFacetBundle(
            advice_facets=[advice_facet],
            image_facets=[image_facet],
            visual_language_facets=[visual_facet],
            relation_facets=[relation_facet],
        )

        legacy_aligned = ProfileAlignedStyleFacetBundle(
            facets=bundle,
            profile_context_present=True,
            alignment_notes=["legacy bundle"],
        )
        explicit_aligned = ProfileAlignedStyleFacetBundle(
            advice_facets=[advice_facet],
            image_facets=[image_facet],
            visual_language_facets=[visual_facet],
            relation_facets=[relation_facet],
            alignment_notes=["explicit bundle"],
        )
        clarification = ProfileClarificationDecision(
            should_ask=True,
            question_text="Do you prefer a softer or more structured silhouette?",
            missing_priority_fields=["silhouette_preferences"],
        )

        self.assertEqual(legacy_aligned.facets.total_count(), 4)
        self.assertEqual(explicit_aligned.facets.total_count(), 4)
        self.assertEqual(explicit_aligned.total_count(), 4)
        self.assertEqual(legacy_aligned.advice_facets[0].style_id, 12)
        self.assertTrue(clarification.should_ask)
        self.assertEqual(
            clarification.missing_priority_fields,
            ["silhouette_preferences"],
        )

    def test_reasoning_input_supports_richer_style_facets_and_knowledge_context(self) -> None:
        knowledge_card = KnowledgeCard(
            id="advice:1",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            title="Advice",
            summary="Use refined contrast.",
        )
        input_contract = FashionReasoningInput(
            mode="style_exploration",
            user_request="Build an outfit around soft futurism.",
            profile_context=ProfileContextSnapshot(values={"height_cm": 175}, present=True),
            style_history=[
                UsedStyleReference(
                    style_id=7,
                    style_name="Cyber Fairy Grunge",
                    palette=["charcoal"],
                    hero_garments=["mesh top"],
                )
            ],
            active_slots={"occasion": "gallery"},
            visual_intent_signal="advice_only",
            visual_intent_required=True,
            knowledge_context=KnowledgeContext(
                providers_used=["style_ingestion"],
                knowledge_cards=[knowledge_card],
                style_cards=[
                    StyleKnowledgeCard(
                        style_id=12,
                        title="Soft Futurism",
                        summary="Fluid techwear with pale light.",
                    )
                ],
                style_advice_cards=[knowledge_card],
                style_visual_cards=[knowledge_card],
            ),
            generation_intent=False,
            can_generate_now=False,
            retrieval_profile="style_focused",
            style_context=[
                StyleKnowledgeCard(style_id=12, title="Soft Futurism", summary="Fluid techwear.")
            ],
            style_advice_facets=[
                StyleAdviceFacet(
                    style_id=12,
                    core_style_logic=["soften utilitarian edges"],
                    styling_rules=["mix translucent and matte textures"],
                    negative_guidance=["avoid hard tactical cosplay"],
                )
            ],
            style_image_facets=[
                StyleImageFacet(
                    style_id=12,
                    hero_garments=["translucent shell jacket"],
                    props=["chrome headphones"],
                    composition_cues=["asymmetric flatlay"],
                )
            ],
            style_visual_language_facets=[
                StyleVisualLanguageFacet(
                    style_id=12,
                    palette=["ice blue", "pearl", "graphite"],
                    lighting_mood=["diffused studio glow"],
                    photo_treatment=["soft bloom"],
                )
            ],
            style_relation_facets=[
                StyleRelationFacet(
                    style_id=12,
                    related_styles=["Y2K futurism"],
                    historical_relations=["space-age minimalism"],
                )
            ],
            style_semantic_fragments=[
                StyleSemanticFragmentSummary(
                    style_id=12,
                    fragment_type="visual_language",
                    summary="Pearlescent light and soft technical surfaces.",
                )
            ],
        )

        bundle = input_contract.style_facet_bundle()
        aligned_bundle = ProfileAlignedStyleFacetBundle(
            facets=bundle,
            profile_context_present=True,
            alignment_notes=["height-aware silhouette weighting"],
        )

        self.assertIsInstance(bundle, StyleFacetBundle)
        self.assertIsInstance(aligned_bundle, ProfileAlignedStyleFacetBundle)
        self.assertEqual(bundle.total_count(), 4)
        self.assertEqual(aligned_bundle.facets.total_count(), 4)
        self.assertEqual(input_contract.knowledge_context.providers_used, ["style_ingestion"])
        self.assertEqual(input_contract.observability_counts()["style_facets_count"], 4)
        self.assertEqual(input_contract.observability_counts()["style_image_facets_count"], 1)
        self.assertEqual(input_contract.observability_counts()["style_visual_cards"], 1)
        self.assertEqual(input_contract.visual_intent_signal, "advice_only")
        self.assertTrue(input_contract.visual_intent_required)
        self.assertEqual(input_contract.observability_counts()["visual_intent_signal_present"], 1)
        self.assertEqual(input_contract.observability_counts()["visual_intent_required"], 1)

    def test_fashion_reasoning_output_carries_voice_and_generation_handoff_signals(self) -> None:
        brief = FashionBrief(
            style_identity="Soft Futurism",
            brief_mode="style_exploration",
            hero_garments=["translucent shell jacket"],
            garment_list=["wide-leg silver trousers"],
            palette=["ice blue", "graphite"],
            props=["chrome headphones"],
            composition_rules=["asymmetric flatlay with negative space"],
            photo_treatment=["soft bloom"],
            source_style_facet_ids=["style-image:12"],
            brief_confidence=0.82,
        )
        output = FashionReasoningOutput(
            response_type="generation_ready",
            text_response="Use a softer technical silhouette with pearlescent contrast.",
            style_logic_points=["soft utility"],
            visual_language_points=["diffused light"],
            historical_note_candidates=["space-age minimalism"],
            styling_rule_candidates=["balance translucent and matte textures"],
            can_offer_visualization=True,
            suggested_cta="Try another style",
            image_cta_candidates=[
                ImageCtaCandidate(
                    cta_text="Visualize this",
                    reason="Image facets are specific enough.",
                    confidence=0.9,
                )
            ],
            fashion_brief=brief,
            generation_ready=True,
        )

        self.assertFalse(output.requires_clarification())
        self.assertTrue(output.has_generation_handoff())
        self.assertIsNone(output.generation_blocked_reason())
        self.assertEqual(
            output.signal_counts(),
            {
                "style_logic_points_count": 1,
                "visual_language_points_count": 1,
                "historical_note_candidates_count": 1,
                "styling_rule_candidates_count": 1,
                "editorial_context_candidates_count": 0,
                "color_poetic_candidates_count": 0,
                "composition_theory_candidates_count": 0,
            },
        )
        self.assertEqual(output.fashion_brief.hero_garments, ["translucent shell jacket"])
        self.assertEqual(output.fashion_brief.props, ["chrome headphones"])
        self.assertEqual(output.fashion_brief.photo_treatment, ["soft bloom"])
        self.assertEqual(output.fashion_brief.intent, "style_exploration")
        self.assertEqual(output.fashion_brief.style_direction, "Soft Futurism")
        self.assertEqual(output.reasoning_metadata, ReasoningMetadata())

    def test_fashion_reasoning_output_reports_generation_blocked_reasons(self) -> None:
        clarification_output = FashionReasoningOutput(
            response_type="clarification",
            text_response="Need the occasion first.",
            clarification_question="What occasion is this for?",
            can_offer_visualization=False,
        )
        text_only_output = FashionReasoningOutput(
            response_type="text",
            text_response="Let's refine the styling direction first.",
            can_offer_visualization=False,
        )
        missing_brief_output = FashionReasoningOutput(
            response_type="visual_offer",
            text_response="I can visualize this next.",
            can_offer_visualization=True,
            generation_ready=False,
        )
        visual_offer_output = FashionReasoningOutput(
            response_type="visual_offer",
            text_response="I can visualize this next.",
            can_offer_visualization=True,
            fashion_brief=FashionBrief(style_identity="Neo Noir", brief_mode="style_exploration"),
            generation_ready=False,
        )

        self.assertEqual(clarification_output.generation_blocked_reason(), "clarification_required")
        self.assertEqual(text_only_output.generation_blocked_reason(), "visualization_not_offered")
        self.assertEqual(missing_brief_output.generation_blocked_reason(), "fashion_brief_missing")
        self.assertEqual(visual_offer_output.generation_blocked_reason(), "generation_not_ready")

    def test_prompt_building_reasoning_input_keeps_backward_compatibility_with_new_fields(self) -> None:
        schema = PromptFashionReasoningInput.model_fields

        for field_name in (
            "user_request",
            "recent_conversation_summary",
            "knowledge_context",
            "profile_context_snapshot",
            "retrieval_profile",
            "style_context",
            "style_advice_facets",
            "style_image_facets",
            "style_visual_language_facets",
            "style_relation_facets",
            "style_semantic_fragments",
        ):
            self.assertIn(field_name, schema)

        reasoning_input = PromptFashionReasoningInput(mode="general_advice", user_message="help")
        self.assertEqual(reasoning_input.effective_user_request(), "help")

    def test_reasoning_application_contracts_are_protocols_without_infrastructure_dependencies(self) -> None:
        self.assertTrue(hasattr(FashionReasoningContextAssembler, "_is_protocol"))
        self.assertTrue(hasattr(ProfileStyleAlignmentService, "_is_protocol"))
        self.assertTrue(hasattr(FashionReasoner, "_is_protocol"))
        self.assertTrue(hasattr(FashionBriefBuilder, "_is_protocol"))
        self.assertTrue(hasattr(FashionReasoningPipeline, "_is_protocol"))
        self.assertTrue(hasattr(ReasoningOutputMapper, "_is_protocol"))

        backend_root = Path(__file__).resolve().parents[1]
        reasoning_paths = [
            backend_root / "app" / "domain" / "reasoning",
            backend_root / "app" / "application" / "reasoning",
        ]
        forbidden_markers = ("from app.models", "import app.models", "from sqlalchemy", "import sqlalchemy")
        violations: list[str] = []

        for directory in reasoning_paths:
            for path in directory.rglob("*.py"):
                source = path.read_text(encoding="utf-8")
                if any(marker in source for marker in forbidden_markers):
                    violations.append(str(path.relative_to(backend_root)))

        self.assertEqual(violations, [])


class FakeReasoningKnowledgeProvider:
    def __init__(self) -> None:
        self.query: ReasoningRetrievalQuery | None = None

    async def retrieve(self, *, query: ReasoningRetrievalQuery) -> KnowledgeContext:
        self.query = query
        return KnowledgeContext(
            providers_used=["fake_style_provider"],
            style_cards=[
                StyleKnowledgeCard(
                    style_id=42,
                    title="Neo Romantic Utility",
                    summary="Utility silhouettes softened by romantic details.",
                )
            ],
        )


class HistoricalKnowledgeProvider:
    async def retrieve(self, *, query: ReasoningRetrievalQuery) -> KnowledgeContext:
        return KnowledgeContext(
            providers_used=["history_editorial_provider"],
            style_cards=[
                StyleKnowledgeCard(
                    style_id=42,
                    title="Neo Romantic Utility",
                    summary="Utility silhouettes softened by romantic details.",
                )
            ],
            knowledge_cards=[
                KnowledgeCard(
                    id="history:1880s",
                    knowledge_type=KnowledgeType.FASHION_HISTORY,
                    title="Belle Epoque",
                    summary="Belle Epoque evening references and elongated linework.",
                )
            ],
            editorial_cards=[
                KnowledgeCard(
                    id="editorial:romantic-revival",
                    knowledge_type=KnowledgeType.STYLE_CATALOG,
                    title="Editorial revival",
                    summary="Editorial revival through softened romantic utility framing.",
                )
            ],
        )


class FakeStyleFacetProvider:
    def __init__(self) -> None:
        self.query: ReasoningRetrievalQuery | None = None

    async def load_facets(self, *, query: ReasoningRetrievalQuery) -> StyleFacetBundle:
        self.query = query
        return StyleFacetBundle(
            advice_facets=[
                StyleAdviceFacet(
                    style_id=42,
                    core_style_logic=["balance hard utility with softer romantic codes"],
                    styling_rules=["anchor volume with a clean waistline"],
                )
            ],
            image_facets=[
                StyleImageFacet(
                    style_id=42,
                    hero_garments=["structured cargo skirt"],
                    composition_cues=["editorial three-quarter pose"],
                )
            ],
            visual_language_facets=[
                StyleVisualLanguageFacet(
                    style_id=42,
                    palette=["moss", "ivory"],
                    lighting_mood=["window-lit softness"],
                )
            ],
            relation_facets=[
                StyleRelationFacet(
                    style_id=42,
                    related_styles=["Romantic Academia"],
                )
            ],
        )


class FakeKnowledgeContextAssembler:
    def __init__(self, context: KnowledgeContext | None = None) -> None:
        self.query: KnowledgeQuery | None = None
        self._context = context or KnowledgeContext()

    async def assemble(self, query: KnowledgeQuery) -> KnowledgeContext:
        self.query = query
        context = self._context.model_copy(deep=True)
        if context.observability:
            return context
        return context.model_copy(
            update={
                "observability": {
                    "knowledge_query_mode": query.mode,
                    "knowledge_retrieval_profile": query.retrieval_profile,
                    "knowledge_provider_count": len(context.providers_used),
                    "knowledge_providers_used": list(context.providers_used),
                    "knowledge_cards_per_provider": {
                        provider: len(
                            [
                                card
                                for card in context.knowledge_cards
                                if (card.provider_code or "").strip().lower() == provider.strip().lower()
                            ]
                        )
                        for provider in context.providers_used
                    },
                    "knowledge_empty_providers": [],
                    "knowledge_provider_latency_ms": {},
                    "knowledge_duplicate_cards_filtered_count": 0,
                    "knowledge_cards_filtered_out_count": 0,
                    "knowledge_ranking_summary": {
                        "ranking_applied": False,
                        "input_cards": len(context.knowledge_cards),
                        "ranked_cards": len(context.knowledge_cards),
                        "returned_cards": len(context.knowledge_cards),
                    },
                    "style_provider_projected_cards_count": len(
                        [
                            card
                            for card in context.knowledge_cards
                            if (card.provider_code or "").strip().lower() == "style_ingestion"
                        ]
                    ),
                    "style_provider_knowledge_types": sorted(
                        {
                            card.knowledge_type.value
                            for card in context.knowledge_cards
                            if (card.provider_code or "").strip().lower() == "style_ingestion"
                        }
                    ),
                    "style_provider_projection_versions": sorted(
                        {
                            str(card.metadata.get("projection_version")).strip()
                            for card in context.knowledge_cards
                            if (card.provider_code or "").strip().lower() == "style_ingestion"
                            and str(card.metadata.get("projection_version") or "").strip()
                        }
                    ),
                    "style_provider_parser_versions": sorted(
                        {
                            str(card.metadata.get("parser_version")).strip()
                            for card in context.knowledge_cards
                            if (card.provider_code or "").strip().lower() == "style_ingestion"
                            and str(card.metadata.get("parser_version") or "").strip()
                        }
                    ),
                    "style_provider_low_richness_styles": [],
                    "style_provider_legacy_summary_fallback_styles": [],
                }
            },
            deep=True,
        )


class FakeKnowledgeRuntimeSettingsProvider:
    def __init__(self, runtime_flags: KnowledgeRuntimeFlags) -> None:
        self._runtime_flags = runtime_flags

    async def get_runtime_flags(self) -> KnowledgeRuntimeFlags:
        return self._runtime_flags

    async def get_provider_priorities(self) -> dict[str, int]:
        return {}


def build_rich_knowledge_context() -> KnowledgeContext:
    advice_card = KnowledgeCard(
        id="style_rules:neo-romantic-utility",
        knowledge_type=KnowledgeType.STYLE_STYLING_RULES,
        provider_code="style_ingestion",
        title="Neo Romantic Utility rules",
        summary="Balance structure and softness through romantic detailing.",
        style_id="neo-romantic-utility",
        metadata={
            "style_numeric_id": 42,
            "projection_version": "style-facet-projector.v1",
            "parser_version": "1",
            "core_style_logic": ["balance structure and softness through romantic detailing"],
            "styling_rules": ["keep the waist defined"],
            "casual_adaptations": ["soften utility pieces with fluid texture"],
        },
    )
    image_card = KnowledgeCard(
        id="style_image:neo-romantic-utility",
        knowledge_type=KnowledgeType.STYLE_IMAGE_COMPOSITION,
        provider_code="style_ingestion",
        title="Neo Romantic Utility composition",
        summary="Editorial three-quarter pose with softened structure.",
        style_id="neo-romantic-utility",
        metadata={
            "style_numeric_id": 42,
            "projection_version": "style-facet-projector.v1",
            "parser_version": "1",
            "hero_garments": ["structured cargo skirt"],
            "props": ["soft leather gloves"],
            "composition_cues": ["editorial three-quarter pose"],
        },
    )
    visual_card = KnowledgeCard(
        id="style_visual:neo-romantic-utility",
        knowledge_type=KnowledgeType.STYLE_VISUAL_LANGUAGE,
        provider_code="style_ingestion",
        title="Neo Romantic Utility visual language",
        summary="Window-lit softness in moss and ivory.",
        style_id="neo-romantic-utility",
        metadata={
            "style_numeric_id": 42,
            "projection_version": "style-facet-projector.v1",
            "parser_version": "1",
            "palette": ["moss", "ivory"],
            "lighting_mood": ["window-lit softness"],
            "photo_treatment": ["soft grain"],
            "mood_keywords": ["editorial calm"],
            "visual_motifs": ["layered drape"],
        },
    )
    relation_card = KnowledgeCard(
        id="style_relation:neo-romantic-utility",
        knowledge_type=KnowledgeType.STYLE_RELATION_CONTEXT,
        provider_code="style_ingestion",
        title="Neo Romantic Utility relations",
        summary="Adjacent to Romantic Academia with softened post-punk structure.",
        style_id="neo-romantic-utility",
        metadata={
            "style_numeric_id": 42,
            "projection_version": "style-facet-projector.v1",
            "parser_version": "1",
            "related_styles": ["Romantic Academia"],
            "historical_context": ["softened post-punk structure"],
            "brands": ["Miu Miu"],
            "platforms": ["editorial lookbook"],
        },
    )
    history_card = KnowledgeCard(
        id="fashion_history:neo-romantic-utility",
        knowledge_type=KnowledgeType.FASHION_HISTORY,
        provider_code="fashion_historian",
        title="Belle Epoque echo",
        summary="Belle Epoque evening references and elongated linework.",
        style_id="neo-romantic-utility",
    )
    editorial_card = KnowledgeCard(
        id="editorial:neo-romantic-utility",
        knowledge_type=KnowledgeType.STYLE_CATALOG,
        provider_code="fashion_historian",
        title="Editorial framing",
        summary="Editorial revival through softened romantic utility framing.",
        style_id="neo-romantic-utility",
    )
    return KnowledgeContext(
        providers_used=["style_ingestion", "fashion_historian"],
        knowledge_cards=[
            advice_card,
            image_card,
            visual_card,
            relation_card,
            history_card,
            editorial_card,
        ],
        style_cards=[
            StyleKnowledgeCard(
                style_id=42,
                title="Neo Romantic Utility",
                summary="Utility silhouettes softened by romantic details.",
            )
        ],
        style_advice_cards=[advice_card],
        style_visual_cards=[visual_card, image_card],
        style_history_cards=[relation_card, history_card],
        editorial_cards=[editorial_card],
    )


class RepeatHeavyStyleFacetProvider:
    async def load_facets(self, *, query: ReasoningRetrievalQuery) -> StyleFacetBundle:
        return StyleFacetBundle(
            advice_facets=[
                StyleAdviceFacet(
                    style_id=77,
                    core_style_logic=["reuse classic academic structure with a softer finish"],
                    styling_rules=["shift the repeated blazer into a lighter outer layer"],
                    negative_guidance=["avoid exact repeat of prior dark academia styling"],
                )
            ],
            image_facets=[
                StyleImageFacet(
                    style_id=77,
                    hero_garments=["wool blazer", "structured cargo skirt"],
                    secondary_garments=["ivory knit top"],
                    core_accessories=["antique brooch"],
                    composition_cues=["editorial three-quarter pose"],
                )
            ],
            visual_language_facets=[
                StyleVisualLanguageFacet(
                    style_id=77,
                    palette=["espresso", "ivory"],
                    lighting_mood=["window-lit softness"],
                    visual_motifs=["relaxed layering", "antique campus drama"],
                )
            ],
            relation_facets=[
                StyleRelationFacet(style_id=77, related_styles=["Romantic Academia"])
            ],
        )


class AdviceOnlyStyleFacetProvider:
    async def load_facets(self, *, query: ReasoningRetrievalQuery) -> StyleFacetBundle:
        return StyleFacetBundle(
            advice_facets=[
                StyleAdviceFacet(
                    style_id=55,
                    core_style_logic=["keep the structure polished but relaxed for real wear"],
                    styling_rules=["let the outfit breathe instead of over-layering"],
                    casual_adaptations=["swap rigid tailoring for softer separates"],
                    statement_pieces=["pleated midi skirt"],
                    status_markers=["sleek belt"],
                    historical_notes=["echoes modernized heritage dressing"],
                )
            ],
            relation_facets=[
                StyleRelationFacet(
                    style_id=55,
                    related_styles=["Soft Retro Prep"],
                    historical_relations=["modern heritage dressing"],
                )
            ],
        )


class FakeStyleHistoryProvider:
    async def load_history(
        self,
        *,
        session_state: SessionStateSnapshot,
        query: ReasoningRetrievalQuery,
    ) -> list[UsedStyleReference]:
        return [
            UsedStyleReference(
                style_id=8,
                style_name="Dark Academia",
                silhouette_family="relaxed layering",
                palette=["espresso"],
                hero_garments=["wool blazer"],
                visual_motifs=["relaxed layering"],
            )
        ]


class FakeDiversityConstraintsProvider:
    async def build_constraints(
        self,
        *,
        session_state: SessionStateSnapshot,
        query: ReasoningRetrievalQuery,
        style_history: list[UsedStyleReference],
        style_facets: StyleFacetBundle,
    ) -> DiversityConstraints | None:
        return DiversityConstraints(
            avoid_silhouette_families=["relaxed layering"],
            avoid_palette=["espresso"],
            avoid_hero_garments=["wool blazer"],
        )


class FakeSemanticFragmentProvider:
    async def load_fragments(self, *, query: ReasoningRetrievalQuery) -> list[StyleSemanticFragmentSummary]:
        return [
            StyleSemanticFragmentSummary(
                style_id=42,
                fragment_type="styling_rule",
                summary="Softening utility pieces is central to this direction.",
            )
        ]


class SemanticOnlyFragmentProvider:
    async def load_fragments(self, *, query: ReasoningRetrievalQuery) -> list[StyleSemanticFragmentSummary]:
        return [
            StyleSemanticFragmentSummary(
                style_id=42,
                fragment_type="advice",
                summary="Use softened utility structure as the main styling logic.",
            ),
            StyleSemanticFragmentSummary(
                style_id=42,
                fragment_type="visual_language",
                summary="ivory palette with window-lit softness",
            ),
            StyleSemanticFragmentSummary(
                style_id=42,
                fragment_type="image_composition",
                summary="editorial three-quarter composition with negative space",
            ),
            StyleSemanticFragmentSummary(
                style_id=42,
                fragment_type="relations",
                summary="adjacent to Romantic Academia",
            ),
        ]


class ReasoningContextAssemblerTests(unittest.IsolatedAsyncioTestCase):
    async def test_assembler_loads_retrieval_context_into_reasoning_input(self) -> None:
        knowledge_provider = FakeReasoningKnowledgeProvider()
        facet_provider = FakeStyleFacetProvider()
        assembler = DefaultFashionReasoningContextAssembler(
            knowledge_provider=knowledge_provider,
            style_facet_provider=facet_provider,
            style_history_provider=FakeStyleHistoryProvider(),
            diversity_constraints_provider=FakeDiversityConstraintsProvider(),
            semantic_fragment_provider=FakeSemanticFragmentProvider(),
        )

        reasoning_input = await assembler.assemble(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Try a softer utility look.",
                recent_conversation_summary="User liked structured but feminine outfits.",
                active_slots={"occasion": "gallery"},
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=ProfileContextSnapshot(values={"fit": "relaxed"}, present=True),
            retrieval_profile=None,
        )

        self.assertEqual(reasoning_input.mode, "style_exploration")
        self.assertEqual(reasoning_input.retrieval_profile, "visual_heavy")
        self.assertEqual(reasoning_input.knowledge_context.providers_used, ["fake_style_provider"])
        self.assertEqual(reasoning_input.style_context[0].title, "Neo Romantic Utility")
        self.assertEqual(reasoning_input.knowledge_context.style_history_cards[0].title, "Dark Academia")
        self.assertEqual(
            reasoning_input.knowledge_context.style_history_cards[0].metadata["silhouette_family"],
            "relaxed layering",
        )
        self.assertEqual(reasoning_input.style_facet_bundle().total_count(), 4)
        self.assertEqual(reasoning_input.style_history[0].style_name, "Dark Academia")
        self.assertEqual(reasoning_input.style_history[0].silhouette_family, "relaxed layering")
        self.assertIn("relaxed layering", reasoning_input.knowledge_context.style_history_cards[0].summary)
        self.assertEqual(reasoning_input.diversity_constraints.avoid_silhouette_families, ["relaxed layering"])
        self.assertEqual(reasoning_input.diversity_constraints.avoid_palette, ["espresso"])
        self.assertEqual(reasoning_input.style_semantic_fragments[0].fragment_type, "styling_rule")
        self.assertEqual(reasoning_input.observability_counts()["style_history_cards"], 1)
        self.assertEqual(knowledge_provider.query.retrieval_profile, "visual_heavy")
        self.assertEqual(facet_provider.query.active_slots, {"occasion": "gallery"})

    async def test_assembler_can_build_reasoning_inputs_from_central_knowledge_context(self) -> None:
        knowledge_context_assembler = FakeKnowledgeContextAssembler(build_rich_knowledge_context())
        assembler = DefaultFashionReasoningContextAssembler(
            knowledge_context_assembler=knowledge_context_assembler,
            knowledge_runtime_flags=KnowledgeRuntimeFlags(
                use_historical_context=True,
                use_editorial_knowledge=True,
                use_color_poetics=True,
            ),
        )

        reasoning_input = await assembler.assemble(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a romantic utility direction I could visualize later.",
                active_slots={"occasion": "gallery"},
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=ProfileContextSnapshot(values={"fit": "relaxed"}, present=True),
            retrieval_profile=None,
        )

        assert knowledge_context_assembler.query is not None
        self.assertEqual(knowledge_context_assembler.query.retrieval_profile, "visual_heavy")
        self.assertTrue(knowledge_context_assembler.query.need_styling_rules)
        self.assertTrue(knowledge_context_assembler.query.need_visual_knowledge)
        self.assertEqual(
            knowledge_context_assembler.query.profile_context["fit_preferences"],
            ["relaxed"],
        )
        self.assertEqual(
            reasoning_input.knowledge_context.providers_used,
            ["style_ingestion", "fashion_historian"],
        )
        self.assertEqual(reasoning_input.style_context[0].title, "Neo Romantic Utility")
        self.assertEqual(reasoning_input.style_facet_bundle().total_count(), 4)
        self.assertEqual(
            reasoning_input.style_advice_facets[0].styling_rules,
            ["keep the waist defined"],
        )
        self.assertEqual(
            reasoning_input.style_relation_facets[0].related_styles,
            ["Romantic Academia"],
        )
        self.assertGreaterEqual(len(reasoning_input.style_semantic_fragments), 4)
        self.assertEqual(
            {fragment.fragment_type for fragment in reasoning_input.style_semantic_fragments},
            {"advice", "image_composition", "relations", "visual_language"},
        )
        self.assertEqual(reasoning_input.observability_counts()["style_history_cards"], 2)
        self.assertEqual(reasoning_input.knowledge_context.editorial_cards[0].provider_code, "fashion_historian")

    def test_retrieval_profile_selector_keeps_explicit_profiles_and_defaults_by_mode(self) -> None:
        selector = DefaultRetrievalProfileSelector()

        explicit = selector.select(
            routing_decision=RoutingDecision(mode=RoutingMode.GENERAL_ADVICE),
            session_state=SessionStateSnapshot(user_request="help"),
            requested_profile="custom_provider_profile",
        )
        occasion = selector.select(
            routing_decision=RoutingDecision(mode=RoutingMode.OCCASION_OUTFIT),
            session_state=SessionStateSnapshot(user_request="outfit for dinner"),
            requested_profile=None,
        )

        self.assertEqual(explicit, "custom_provider_profile")
        self.assertEqual(occasion, "occasion_focused")

    async def test_assembler_accepts_router_retrieval_profile_hint(self) -> None:
        assembler = DefaultFashionReasoningContextAssembler()

        reasoning_input = await assembler.assemble(
            routing_decision=RoutingDecision(
                mode=RoutingMode.GENERAL_ADVICE,
                retrieval_profile="style_focused",
            ),
            session_state=SessionStateSnapshot(user_request="Explain this style direction."),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertEqual(reasoning_input.retrieval_profile, "style_focused")

    async def test_assembler_carries_visual_intent_signal_and_requirement_into_reasoning_input(self) -> None:
        assembler = DefaultFashionReasoningContextAssembler()

        reasoning_input = await assembler.assemble(
            routing_decision=RoutingDecision(mode=RoutingMode.OCCASION_OUTFIT),
            session_state=SessionStateSnapshot(
                user_request="Build a dinner outfit.",
                active_slots={"occasion": "dinner", "weather": "cool", "visual_intent": "advice_only"},
                visual_intent_required=True,
                metadata={"visual_intent_required": True},
            ),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertEqual(reasoning_input.visual_intent_signal, "advice_only")
        self.assertTrue(reasoning_input.visual_intent_required)

    async def test_assembler_builds_default_diversity_constraints_from_style_history(self) -> None:
        assembler = DefaultFashionReasoningContextAssembler()

        reasoning_input = await assembler.assemble(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Try another direction.",
                can_generate_now=True,
                style_history=[
                    UsedStyleReference(
                        style_id=4,
                        style_name="Soft Retro Prep",
                        silhouette_family="structured collegiate",
                        palette=["camel", "cream"],
                        hero_garments=["camel blazer"],
                    )
                ],
            ),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertEqual(
            reasoning_input.diversity_constraints.avoid_silhouette_families,
            ["structured collegiate"],
        )
        self.assertEqual(reasoning_input.diversity_constraints.avoid_palette, ["camel", "cream"])
        self.assertEqual(reasoning_input.diversity_constraints.avoid_hero_garments, ["camel blazer"])
        self.assertEqual(reasoning_input.diversity_constraints.target_visual_distance, "high")


class FakeStyleCatalogSearchRepository:
    def __init__(self) -> None:
        self.query = None

    async def search(self, *, query):
        self.query = query
        return [
            KnowledgeCard(
                id="style_catalog:soft-retro-prep",
                knowledge_type=KnowledgeType.STYLE_CATALOG,
                title="Soft Retro Prep",
                summary="Soft collegiate dressing with warm structure.",
                style_id="soft-retro-prep",
                source_ref="style://soft-retro-prep",
                confidence=0.88,
                metadata={
                    "style_numeric_id": 101,
                    "core_style_logic": ["Blend collegiate structure with softened warmth."],
                    "styling_rules": ["Keep prep elements edited and breathable."],
                    "casual_adaptations": ["Use softer knits instead of stiff layers."],
                    "statement_pieces": ["camel blazer"],
                    "status_markers": ["heritage loafers"],
                    "overlap_context": ["bridges prep and retro casual dressing"],
                    "historical_notes": ["References collegiate heritage."],
                    "negative_guidance": ["Avoid neon accents."],
                    "hero_garments": ["camel blazer", "oxford shirt"],
                    "secondary_garments": ["pleated chinos"],
                    "core_accessories": ["belt"],
                    "props": ["folded magazine"],
                    "composition_cues": ["leave breathing room between garments"],
                    "negative_constraints": ["avoid neon"],
                    "palette": ["camel", "cream", "navy"],
                    "lighting_mood": ["soft daylight"],
                    "photo_treatment": ["editorial grain"],
                    "mood_keywords": ["warm", "polished"],
                    "visual_motifs": ["relaxed layering"],
                    "platform_visual_cues": ["quiet luxury editorial"],
                    "related_styles": ["ivy style"],
                    "overlap_styles": ["retro prep"],
                    "preceded_by": ["classic prep"],
                    "brands": ["Ralph Lauren"],
                    "platforms": ["editorial lookbook"],
                },
            )
        ]


class StyleDistilledReasoningProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_projects_style_catalog_cards_into_reasoning_contracts(self) -> None:
        repository = FakeStyleCatalogSearchRepository()
        provider = StyleDistilledReasoningProvider(style_catalog_repository=repository)
        query = ReasoningRetrievalQuery(
            mode="style_exploration",
            user_request="Make retro prep softer.",
            retrieval_profile="visual_heavy",
            generation_intent=True,
            current_style_name="Soft Retro Prep",
        )

        knowledge_context = await provider.retrieve(query=query)
        facets = await provider.load_facets(query=query)
        fragments = await provider.load_fragments(query=query)

        self.assertEqual(repository.query.style_name, "Soft Retro Prep")
        self.assertEqual(repository.query.intent, "visual")
        self.assertEqual(repository.query.limit, 10)
        self.assertEqual(knowledge_context.providers_used, ["style_ingestion"])
        self.assertEqual(knowledge_context.style_cards[0].title, "Soft Retro Prep")
        self.assertEqual(knowledge_context.style_advice_cards[0].metadata["style_numeric_id"], 101)
        self.assertEqual(facets.total_count(), 4)
        self.assertEqual(facets.advice_facets[0].style_id, 101)
        self.assertEqual(facets.advice_facets[0].styling_rules, ["Keep prep elements edited and breathable."])
        self.assertEqual(facets.image_facets[0].hero_garments, ["camel blazer", "oxford shirt"])
        self.assertEqual(facets.visual_language_facets[0].lighting_mood, ["soft daylight"])
        self.assertEqual(facets.relation_facets[0].related_styles, ["ivy style"])
        self.assertTrue(any(fragment.fragment_type == "visual_language" for fragment in fragments))


class ProfileStyleAlignmentServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_alignment_filters_conflicting_garments_and_prioritizes_profile_signals(self) -> None:
        service = DefaultProfileStyleAlignmentService()

        result = await service.align(
            profile=ProfileContextSnapshot(
                present=True,
                values={
                    "excluded_garments": ["wool blazer"],
                    "preferred_items": ["relaxed knit top"],
                    "fit": "relaxed",
                    "formality": "casual",
                    "preferred_palette": ["ivory"],
                    "color_avoidances": ["moss"],
                    "preferred_styles": ["neo romantic"],
                    "avoided_styles": ["hard tactical"],
                    "preferred_brands": ["ralph"],
                    "avoided_brands": ["avoid brand"],
                },
            ),
            style_facets=StyleFacetBundle(
                advice_facets=[
                    StyleAdviceFacet(
                        style_id=42,
                        core_style_logic=["structured romance", "relaxed utility balance"],
                        styling_rules=["keep a sharp waist", "relaxed layering for daytime"],
                        casual_adaptations=["casual cotton layer"],
                        statement_pieces=["wool blazer", "cargo skirt"],
                    )
                ],
                image_facets=[
                    StyleImageFacet(
                        style_id=42,
                        hero_garments=["wool blazer", "structured cargo skirt"],
                        secondary_garments=["relaxed knit top"],
                        composition_cues=["formal editorial pose", "relaxed diagonal flatlay"],
                    )
                ],
                visual_language_facets=[
                    StyleVisualLanguageFacet(
                        style_id=42,
                        palette=["moss", "ivory"],
                    )
                ],
                relation_facets=[
                    StyleRelationFacet(
                        style_id=42,
                        related_styles=["hard tactical", "Neo Romantic Utility"],
                        brands=["Avoid Brand", "Ralph Lauren"],
                    )
                ],
            ),
        )

        aligned = result.facets

        self.assertTrue(result.profile_context_present)
        self.assertIn("wool blazer", result.filtered_out)
        self.assertIn("moss", result.filtered_out)
        self.assertIn("hard tactical", result.filtered_out)
        self.assertIn("Avoid Brand", result.filtered_out)
        self.assertEqual(
            result.boosted_facet_categories,
            ["advice", "image", "visual_language", "relation"],
        )
        self.assertEqual(
            result.removed_item_types,
            ["garments_and_accessories", "palette", "relation"],
        )
        self.assertEqual(aligned.image_facets[0].hero_garments, ["structured cargo skirt"])
        self.assertEqual(aligned.advice_facets[0].statement_pieces, ["cargo skirt"])
        self.assertEqual(aligned.advice_facets[0].core_style_logic[0], "relaxed utility balance")
        self.assertEqual(aligned.advice_facets[0].styling_rules[0], "casual cotton layer")
        self.assertEqual(aligned.image_facets[0].composition_cues[0], "relaxed diagonal flatlay")
        self.assertEqual(aligned.visual_language_facets[0].palette, ["ivory"])
        self.assertEqual(aligned.relation_facets[0].related_styles, ["Neo Romantic Utility"])
        self.assertEqual(aligned.relation_facets[0].brands, ["Ralph Lauren"])
        self.assertGreater(result.facet_weights["advice:42"], 1.0)
        self.assertGreater(result.facet_weights["image:42"], 1.0)
        self.assertGreater(result.facet_weights["visual:42"], 1.0)
        self.assertGreater(result.facet_weights["relation:42"], 1.0)

    async def test_alignment_applies_soft_penalties_and_wearable_adaptation_without_hard_deletion(self) -> None:
        service = DefaultProfileStyleAlignmentService()

        result = await service.align(
            profile=ProfileContextSnapshot(
                present=True,
                values={
                    "presentation_profile": "androgynous",
                    "silhouette_preferences": ["structured"],
                    "comfort_preferences": ["high_comfort"],
                    "formality_preferences": ["smart_casual"],
                },
            ),
            style_facets=StyleFacetBundle(
                advice_facets=[
                    StyleAdviceFacet(
                        style_id=77,
                        core_style_logic=[
                            "soft romantic drape",
                            "structured clean tailoring",
                        ],
                        styling_rules=[
                            "romantic ruffles with delicate heel",
                            "clean longline layers",
                        ],
                        casual_adaptations=[
                            "soft knit blazer",
                        ],
                        statement_pieces=[
                            "fragile feather heel",
                            "architectural vest",
                        ],
                        status_markers=[
                            "crystal clutch",
                            "clean loafers",
                        ],
                    )
                ],
                image_facets=[
                    StyleImageFacet(
                        style_id=77,
                        hero_garments=[
                            "ruffled blouse",
                            "tailored long coat",
                        ],
                        core_accessories=[
                            "stiletto heels",
                            "clean loafers",
                        ],
                        composition_cues=[
                            "soft dreamy close crop",
                            "clean vertical flatlay",
                        ],
                    )
                ],
                visual_language_facets=[
                    StyleVisualLanguageFacet(
                        style_id=77,
                        mood_keywords=["ornate romance", "clean restraint"],
                        visual_motifs=["ruffled softness", "clean linework"],
                    )
                ],
            ),
        )

        aligned = result.facets

        self.assertEqual(
            aligned.advice_facets[0].core_style_logic[0],
            "structured clean tailoring",
        )
        self.assertEqual(
            aligned.advice_facets[0].styling_rules[0],
            "soft knit blazer",
        )
        self.assertEqual(
            aligned.advice_facets[0].statement_pieces[0],
            "architectural vest",
        )
        self.assertEqual(
            aligned.image_facets[0].hero_garments[0],
            "tailored long coat",
        )
        self.assertEqual(
            aligned.image_facets[0].core_accessories[0],
            "clean loafers",
        )
        self.assertIn("stiletto heels", aligned.image_facets[0].core_accessories)
        self.assertEqual(
            aligned.image_facets[0].composition_cues[0],
            "clean vertical flatlay",
        )
        self.assertEqual(
            aligned.visual_language_facets[0].visual_motifs[0],
            "clean linework",
        )
        self.assertIn(
            "boosted presentation-relevant cues across aligned facets",
            result.alignment_notes,
        )
        self.assertIn(
            "softly de-emphasized cues that conflict with profile silhouette, comfort, or presentation",
            result.alignment_notes,
        )
        self.assertIn(
            "softened editorial emphasis toward more wearable profile-aligned adaptations",
            result.alignment_notes,
        )


class ProfileAlignedReasoningContextAssemblerTests(unittest.IsolatedAsyncioTestCase):
    async def test_profile_aligned_assembler_places_aligned_facets_before_reasoning(self) -> None:
        assembler = ProfileAlignedFashionReasoningContextAssembler(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=FakeStyleFacetProvider(),
            ),
            alignment_service=DefaultProfileStyleAlignmentService(),
        )

        reasoning_input = await assembler.assemble(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Make it softer and avoid the cargo skirt.",
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=ProfileContextSnapshot(
                present=True,
                values={"excluded_garments": ["structured cargo skirt"], "preferred_palette": "ivory"},
            ),
            retrieval_profile=None,
        )

        self.assertEqual(reasoning_input.style_image_facets[0].hero_garments, [])
        self.assertEqual(reasoning_input.style_visual_language_facets[0].palette[0], "ivory")
        self.assertTrue(reasoning_input.profile_alignment_applied)
        self.assertTrue(reasoning_input.profile_alignment_notes)
        self.assertIn("structured cargo skirt", reasoning_input.profile_alignment_filtered_out)
        self.assertIn("visual_language", reasoning_input.profile_alignment_boosted_categories)
        self.assertIn("garments_and_accessories", reasoning_input.profile_alignment_removed_item_types)
        self.assertIn("image:42", reasoning_input.profile_facet_weights)


class DefaultFashionReasonerTests(unittest.IsolatedAsyncioTestCase):
    async def test_reasoner_uses_profile_clarification_policy_when_it_requests_profile_question(self) -> None:
        class AlwaysAskProfilePolicy:
            async def evaluate(self, *, mode, profile, style_bundle):
                return ProfileClarificationDecision(
                    should_ask=True,
                    question_text="Which presentation direction should guide this look?",
                    missing_priority_fields=["presentation_profile"],
                )

        reasoner = DefaultFashionReasoner(
            profile_clarification_policy=AlwaysAskProfilePolicy(),
        )

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="style_exploration",
                user_request="Build a sharper version of this style direction.",
                style_advice_facets=[
                    StyleAdviceFacet(style_id=12, core_style_logic=["clean tailoring"])
                ],
            )
        )

        self.assertTrue(output.requires_clarification())
        self.assertEqual(
            output.clarification_question,
            "Which presentation direction should guide this look?",
        )
        self.assertTrue(output.observability["profile_clarification_required"])
        self.assertEqual(output.observability["profile_clarification_decision"], "asked")
        self.assertEqual(
            output.observability["profile_clarification_missing_priority_fields"],
            ["presentation_profile"],
        )
        self.assertEqual(output.observability["profile_completeness_state"], "missing")

    async def test_reasoner_returns_clarification_without_brief_when_required_slots_are_missing(self) -> None:
        reasoner = DefaultFashionReasoner(
            knowledge_runtime_flags=KnowledgeRuntimeFlags(
                use_historical_context=True,
                use_editorial_knowledge=True,
            )
        )

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="occasion_outfit",
                user_request="Build me a look.",
                active_slots={},
            )
        )

        self.assertTrue(output.requires_clarification())
        self.assertIsNotNone(output.clarification_question)
        self.assertIsNone(output.fashion_brief)
        self.assertFalse(output.can_offer_visualization)

    async def test_reasoner_requests_silhouette_preference_for_occasion_outfit_when_missing(self) -> None:
        reasoner = DefaultFashionReasoner()

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="occasion_outfit",
                user_request="Build me a dinner outfit.",
                active_slots={"occasion": "dinner", "weather": "cool evening"},
            )
        )

        self.assertTrue(output.requires_clarification())
        self.assertEqual(
            output.clarification_question,
            "Do you prefer a relaxed, fitted, or oversized silhouette for this look?",
        )
        self.assertIsNone(output.fashion_brief)
        self.assertFalse(output.can_offer_visualization)
        self.assertEqual(output.observability["profile_clarification_decision"], "asked")

    async def test_reasoner_requests_presentation_direction_for_partial_style_exploration_profile(self) -> None:
        reasoner = DefaultFashionReasoner()

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="style_exploration",
                user_request="Show another tailored direction.",
                profile_context=ProfileContextSnapshot(
                    silhouette_preferences=("structured",),
                    source="test",
                ),
                style_advice_facets=[
                    StyleAdviceFacet(
                        style_id=21,
                        core_style_logic=["keep the lines clean and deliberate"],
                    )
                ],
            )
        )

        self.assertTrue(output.requires_clarification())
        self.assertEqual(
            output.clarification_question,
            "Which presentation direction should guide this look: feminine, masculine, androgynous, or universal?",
        )
        self.assertIsNone(output.fashion_brief)
        self.assertFalse(output.can_offer_visualization)
        self.assertTrue(output.observability["profile_clarification_required"])
        self.assertEqual(output.observability["profile_clarification_decision"], "asked")
        self.assertEqual(
            output.observability["profile_clarification_missing_priority_fields"],
            ["presentation_profile"],
        )

    async def test_reasoner_requests_wearability_preference_for_branching_style_exploration_bundle(self) -> None:
        reasoner = DefaultFashionReasoner()

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="style_exploration",
                user_request="Show another tailored direction.",
                profile_context=ProfileContextSnapshot(
                    presentation_profile="androgynous",
                    silhouette_preferences=("structured",),
                    source="test",
                ),
                style_advice_facets=[
                    StyleAdviceFacet(
                        style_id=21,
                        casual_adaptations=["swap the heels for loafers"],
                        statement_pieces=["dramatic long coat"],
                    )
                ],
            )
        )

        self.assertTrue(output.requires_clarification())
        self.assertEqual(
            output.clarification_question,
            "Do you want this to stay highly wearable, balanced, or a bit more expressive?",
        )
        self.assertIsNone(output.fashion_brief)
        self.assertFalse(output.can_offer_visualization)
        self.assertTrue(output.observability["profile_clarification_required"])
        self.assertEqual(output.observability["profile_clarification_decision"], "asked")
        self.assertEqual(
            output.observability["profile_clarification_missing_priority_fields"],
            ["comfort_preferences"],
        )

    async def test_reasoner_requests_visual_intent_when_upstream_marks_it_required(self) -> None:
        reasoner = DefaultFashionReasoner()

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="occasion_outfit",
                user_request="Build me a dinner outfit.",
                active_slots={"occasion": "dinner", "weather": "cool evening"},
                visual_intent_required=True,
                profile_context=ProfileContextSnapshot(
                    values={"silhouette": "relaxed"},
                    present=True,
                ),
            )
        )

        self.assertTrue(output.requires_clarification())
        self.assertEqual(
            output.clarification_question,
            "Should I keep this as text advice, or shape it toward a visualizable outfit direction?",
        )
        self.assertIsNone(output.fashion_brief)
        self.assertFalse(output.can_offer_visualization)
        self.assertTrue(output.observability["clarification_required"])
        self.assertTrue(output.observability["visual_intent_required"])
        self.assertFalse(output.observability["visual_intent_signal_present"])

    async def test_reasoner_marks_partial_profile_completeness_when_profile_exists_but_is_incomplete(self) -> None:
        reasoner = DefaultFashionReasoner(
            profile_clarification_policy=DefaultProfileClarificationPolicy(),
        )

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="general_advice",
                user_request="How can I make this cleaner?",
                profile_context=ProfileContextSnapshot(
                    presentation_profile="androgynous",
                    source="test",
                ),
                style_advice_facets=[
                    StyleAdviceFacet(style_id=12, core_style_logic=["reduce noise"])
                ],
            )
        )

        self.assertFalse(output.requires_clarification())
        self.assertEqual(output.observability["profile_completeness_state"], "partial")

    async def test_reasoner_uses_richer_facets_for_structured_output_and_cta_candidates(self) -> None:
        reasoner = DefaultFashionReasoner()

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="style_exploration",
                user_request="Build a soft futurist look.",
                retrieval_profile="visual_heavy",
                generation_intent=True,
                can_generate_now=True,
                knowledge_context=KnowledgeContext(providers_used=["style_ingestion"]),
                style_advice_facets=[
                    StyleAdviceFacet(
                        style_id=12,
                        core_style_logic=["soften technical garments with fluid layers"],
                        overlap_context=["bridges utility dressing and romantic eveningwear"],
                        styling_rules=["balance translucent and matte textures"],
                        historical_notes=["space-age minimalism"],
                    )
                ],
                style_image_facets=[
                    StyleImageFacet(
                        style_id=12,
                        hero_garments=["translucent shell jacket"],
                        core_accessories=["chrome headphones"],
                        composition_cues=["asymmetric flatlay"],
                    )
                ],
                style_visual_language_facets=[
                    StyleVisualLanguageFacet(
                        style_id=12,
                        palette=["ice blue", "graphite"],
                        lighting_mood=["diffused studio glow"],
                        photo_treatment=["soft bloom"],
                        mood_keywords=["luminous", "polished"],
                        platform_visual_cues=["editorial lookbook framing"],
                    )
                ],
                style_relation_facets=[
                    StyleRelationFacet(
                        style_id=12,
                        related_styles=["Y2K futurism"],
                        overlap_styles=["soft cyber romantic"],
                        brands=["Paco Rabanne"],
                        platforms=["editorial lookbook"],
                    )
                ],
            )
        )

        self.assertEqual(output.response_type, "generation_ready")
        self.assertIn("soften technical garments with fluid layers", output.style_logic_points)
        self.assertIn(
            "bridges utility dressing and romantic eveningwear",
            output.style_logic_points,
        )
        self.assertIn("ice blue", output.visual_language_points)
        self.assertIn("luminous", output.visual_language_points)
        self.assertIn("editorial lookbook framing", output.visual_language_points)
        self.assertIn("Y2K futurism", output.historical_note_candidates)
        self.assertIn("overlaps with soft cyber romantic", output.historical_note_candidates)
        self.assertIn("brand reference: Paco Rabanne", output.historical_note_candidates)
        self.assertIn("platform cue: editorial lookbook", output.historical_note_candidates)
        self.assertIn("space-age minimalism", output.historical_note_candidates)
        self.assertTrue(output.can_offer_visualization)
        self.assertEqual(output.image_cta_candidates[0].required_generation_trigger, "generate_now")
        self.assertFalse(output.has_generation_handoff())

    async def test_reasoner_uses_profile_facet_weights_for_downstream_prioritization(self) -> None:
        reasoner = DefaultFashionReasoner()

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="style_exploration",
                user_request="Show a tailored direction.",
                retrieval_profile="visual_heavy",
                generation_intent=True,
                can_generate_now=True,
                profile_alignment_applied=True,
                profile_facet_weights={
                    "advice:1": 1.0,
                    "advice:2": 2.5,
                    "image:1": 1.0,
                    "image:2": 2.5,
                    "visual:1": 1.0,
                    "visual:2": 2.5,
                    "relation:1": 1.0,
                    "relation:2": 2.5,
                },
                style_advice_facets=[
                    StyleAdviceFacet(
                        style_id=1,
                        core_style_logic=["dark structure"],
                        styling_rules=["keep it rigid"],
                        historical_notes=["industrial severity"],
                    ),
                    StyleAdviceFacet(
                        style_id=2,
                        core_style_logic=["soft structure"],
                        styling_rules=["keep it fluid"],
                        historical_notes=["relaxed elegance"],
                    ),
                ],
                style_image_facets=[
                    StyleImageFacet(
                        style_id=1,
                        hero_garments=["black coat"],
                        composition_cues=["front pose"],
                    ),
                    StyleImageFacet(
                        style_id=2,
                        hero_garments=["ivory blazer"],
                        composition_cues=["airy diagonal flatlay"],
                    ),
                ],
                style_visual_language_facets=[
                    StyleVisualLanguageFacet(
                        style_id=1,
                        palette=["black"],
                        lighting_mood=["hard shadow"],
                    ),
                    StyleVisualLanguageFacet(
                        style_id=2,
                        palette=["ivory"],
                        lighting_mood=["soft daylight"],
                    ),
                ],
                style_relation_facets=[
                    StyleRelationFacet(
                        style_id=1,
                        related_styles=["Dark Minimal"],
                        historical_relations=["industrial severity"],
                    ),
                    StyleRelationFacet(
                        style_id=2,
                        related_styles=["Soft Tailoring"],
                        historical_relations=["relaxed elegance"],
                    ),
                ],
            )
        )

        self.assertEqual(output.style_logic_points[0], "soft structure")
        self.assertEqual(output.visual_language_points[0], "ivory")
        self.assertEqual(output.historical_note_candidates[0], "relaxed elegance")
        self.assertIn("soft structure", output.text_response)

    async def test_reasoner_adjusts_cta_confidence_by_generation_intent_and_profile_signals(self) -> None:
        reasoner = DefaultFashionReasoner()
        base_kwargs = {
            "style_advice_facets": [
                StyleAdviceFacet(style_id=12, core_style_logic=["soft structure"])
            ],
            "style_image_facets": [
                StyleImageFacet(
                    style_id=12,
                    hero_garments=["ivory blazer"],
                    core_accessories=["pearl bag"],
                    composition_cues=["airy diagonal flatlay"],
                )
            ],
            "style_visual_language_facets": [
                StyleVisualLanguageFacet(
                    style_id=12,
                    palette=["ivory"],
                    lighting_mood=["soft daylight"],
                )
            ],
        }

        advisory_output = await reasoner.reason(
            FashionReasoningInput(
                mode="general_advice",
                user_request="Explain the direction first.",
                retrieval_profile="style_focused",
                generation_intent=False,
                can_generate_now=True,
                **base_kwargs,
            )
        )
        generation_ready_output = await reasoner.reason(
            FashionReasoningInput(
                mode="style_exploration",
                user_request="Visualize the direction.",
                retrieval_profile="visual_heavy",
                generation_intent=True,
                can_generate_now=True,
                profile_context=ProfileContextSnapshot(
                    presentation_profile="androgynous",
                    fit_preferences=("relaxed",),
                    color_preferences=("ivory",),
                    source="test",
                ),
                profile_alignment_applied=True,
                profile_facet_weights={"visual:12": 2.0, "image:12": 2.0},
                **base_kwargs,
            )
        )

        self.assertTrue(advisory_output.can_offer_visualization)
        self.assertTrue(generation_ready_output.can_offer_visualization)
        self.assertEqual(advisory_output.response_type, "visual_offer")
        self.assertEqual(generation_ready_output.response_type, "generation_ready")
        self.assertTrue(advisory_output.observability["reasoning_is_mostly_advisory"])
        self.assertFalse(generation_ready_output.observability["reasoning_is_mostly_advisory"])
        self.assertFalse(advisory_output.observability["profile_signals_sufficient"])
        self.assertTrue(generation_ready_output.observability["profile_signals_sufficient"])
        self.assertLess(
            advisory_output.image_cta_candidates[0].confidence,
            generation_ready_output.image_cta_candidates[0].confidence,
        )
        self.assertLess(
            advisory_output.observability["cta_confidence_score"],
            generation_ready_output.observability["cta_confidence_score"],
        )

    async def test_reasoner_uses_explicit_visual_intent_signal_to_adjust_visual_offer_confidence(self) -> None:
        reasoner = DefaultFashionReasoner()
        base_kwargs = {
            "mode": "style_exploration",
            "user_request": "Shape the direction first.",
            "retrieval_profile": "visual_heavy",
            "generation_intent": False,
            "can_generate_now": True,
            "style_advice_facets": [
                StyleAdviceFacet(style_id=12, core_style_logic=["soft structure"])
            ],
            "style_image_facets": [
                StyleImageFacet(
                    style_id=12,
                    hero_garments=["ivory blazer"],
                    core_accessories=["pearl bag"],
                    composition_cues=["airy diagonal flatlay"],
                )
            ],
            "style_visual_language_facets": [
                StyleVisualLanguageFacet(
                    style_id=12,
                    palette=["ivory"],
                    lighting_mood=["soft daylight"],
                )
            ],
        }

        advice_only_output = await reasoner.reason(
            FashionReasoningInput(
                visual_intent_signal="advice_only",
                **base_kwargs,
            )
        )
        open_visual_output = await reasoner.reason(
            FashionReasoningInput(
                visual_intent_signal="open_to_visualization",
                **base_kwargs,
            )
        )

        self.assertEqual(advice_only_output.response_type, "visual_offer")
        self.assertEqual(open_visual_output.response_type, "visual_offer")
        self.assertTrue(advice_only_output.can_offer_visualization)
        self.assertTrue(open_visual_output.can_offer_visualization)
        self.assertTrue(advice_only_output.observability["reasoning_is_mostly_advisory"])
        self.assertFalse(open_visual_output.observability["reasoning_is_mostly_advisory"])
        self.assertLess(
            advice_only_output.image_cta_candidates[0].confidence,
            open_visual_output.image_cta_candidates[0].confidence,
        )
        self.assertLess(
            advice_only_output.observability["cta_confidence_score"],
            open_visual_output.observability["cta_confidence_score"],
        )

    async def test_reasoner_downweights_repeated_image_cues_for_visual_offer_confidence(self) -> None:
        reasoner = DefaultFashionReasoner()
        base_kwargs = {
            "mode": "style_exploration",
            "user_request": "Show the direction first.",
            "retrieval_profile": "visual_heavy",
            "generation_intent": False,
            "can_generate_now": True,
            "style_advice_facets": [
                StyleAdviceFacet(style_id=12, core_style_logic=["soft structure"])
            ],
            "style_image_facets": [
                StyleImageFacet(
                    style_id=12,
                    hero_garments=["wool blazer"],
                    core_accessories=["black belt"],
                    composition_cues=["formal studio pose"],
                )
            ],
            "style_visual_language_facets": [
                StyleVisualLanguageFacet(
                    style_id=12,
                    palette=["ivory"],
                    lighting_mood=["soft daylight"],
                )
            ],
        }

        fresh_output = await reasoner.reason(FashionReasoningInput(**base_kwargs))
        repeated_output = await reasoner.reason(
            FashionReasoningInput(
                **base_kwargs,
                diversity_constraints=DiversityConstraints(
                    avoid_hero_garments=["wool blazer"],
                    avoid_accessories=["black belt"],
                    avoid_composition_types=["formal studio pose"],
                ),
            )
        )

        self.assertEqual(fresh_output.response_type, "visual_offer")
        self.assertEqual(repeated_output.response_type, "visual_offer")
        self.assertGreater(
            fresh_output.observability["image_context_strength"],
            repeated_output.observability["image_context_strength"],
        )
        self.assertGreater(
            fresh_output.image_cta_candidates[0].confidence,
            repeated_output.image_cta_candidates[0].confidence,
        )
        self.assertGreater(
            fresh_output.observability["cta_confidence_score"],
            repeated_output.observability["cta_confidence_score"],
        )
        self.assertEqual(repeated_output.observability["anti_repeat_hero_garments_avoided_count"], 1)
        self.assertEqual(repeated_output.observability["anti_repeat_accessories_avoided_count"], 1)
        self.assertEqual(repeated_output.observability["anti_repeat_composition_cues_avoided_count"], 1)

    async def test_reasoner_includes_historical_notes_from_knowledge_and_editorial_cards(self) -> None:
        reasoner = DefaultFashionReasoner(
            knowledge_runtime_flags=KnowledgeRuntimeFlags(
                use_historical_context=True,
                use_editorial_knowledge=True,
            )
        )

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="style_exploration",
                user_request="Build a romantic utility look.",
                retrieval_profile="visual_heavy",
                generation_intent=False,
                can_generate_now=False,
                knowledge_context=KnowledgeContext(
                    providers_used=["history_editorial_provider"],
                    knowledge_cards=[
                        KnowledgeCard(
                            id="history:1880s",
                            knowledge_type=KnowledgeType.FASHION_HISTORY,
                            title="Belle Epoque",
                            summary="Belle Epoque evening references and elongated linework.",
                        )
                    ],
                    editorial_cards=[
                        KnowledgeCard(
                            id="editorial:romantic-revival",
                            knowledge_type=KnowledgeType.STYLE_CATALOG,
                            title="Editorial revival",
                            summary="Editorial revival through softened romantic utility framing.",
                        )
                    ],
                ),
                style_advice_facets=[
                    StyleAdviceFacet(
                        style_id=12,
                        core_style_logic=["soften technical garments with fluid layers"],
                        historical_notes=["space-age minimalism"],
                    )
                ],
                style_image_facets=[
                    StyleImageFacet(
                        style_id=12,
                        hero_garments=["translucent shell jacket"],
                        composition_cues=["asymmetric flatlay"],
                    )
                ],
                style_visual_language_facets=[
                    StyleVisualLanguageFacet(
                        style_id=12,
                        palette=["ice blue", "graphite"],
                        lighting_mood=["diffused studio glow"],
                    )
                ],
                style_relation_facets=[
                    StyleRelationFacet(style_id=12, historical_relations=["Victorian romantic linework"])
                ],
            )
        )

        self.assertIn("Victorian romantic linework", output.historical_note_candidates)
        self.assertIn("space-age minimalism", output.historical_note_candidates)
        self.assertIn(
            "Belle Epoque evening references and elongated linework.",
            output.historical_note_candidates,
        )
        self.assertIn(
            "Editorial revival through softened romantic utility framing.",
            output.historical_note_candidates,
        )
        self.assertIn(
            "Editorial revival through softened romantic utility framing.",
            output.editorial_context_candidates,
        )
        self.assertIn("ice blue", output.color_poetic_candidates)
        self.assertIn("diffused studio glow", output.color_poetic_candidates)
        self.assertIn("asymmetric flatlay", output.composition_theory_candidates)

    async def test_reasoner_respects_runtime_flags_for_historical_and_color_poetic_layers(self) -> None:
        reasoner = DefaultFashionReasoner(
            knowledge_runtime_flags=KnowledgeRuntimeFlags(
                use_historical_context=False,
                use_editorial_knowledge=False,
                use_color_poetics=False,
            )
        )

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="style_exploration",
                user_request="Build a romantic utility look.",
                retrieval_profile="visual_heavy",
                generation_intent=False,
                can_generate_now=False,
                knowledge_context=KnowledgeContext(
                    providers_used=["history_editorial_provider"],
                    knowledge_cards=[
                        KnowledgeCard(
                            id="history:1880s",
                            knowledge_type=KnowledgeType.FASHION_HISTORY,
                            title="Belle Epoque",
                            summary="Belle Epoque evening references and elongated linework.",
                        )
                    ],
                    editorial_cards=[
                        KnowledgeCard(
                            id="editorial:romantic-revival",
                            knowledge_type=KnowledgeType.STYLE_CATALOG,
                            title="Editorial revival",
                            summary="Editorial revival through softened romantic utility framing.",
                        )
                    ],
                ),
                style_advice_facets=[
                    StyleAdviceFacet(
                        style_id=12,
                        core_style_logic=["soften technical garments with fluid layers"],
                        historical_notes=["space-age minimalism"],
                    )
                ],
                style_image_facets=[
                    StyleImageFacet(
                        style_id=12,
                        hero_garments=["translucent shell jacket"],
                        composition_cues=["asymmetric flatlay"],
                    )
                ],
                style_visual_language_facets=[
                    StyleVisualLanguageFacet(
                        style_id=12,
                        palette=["ice blue", "graphite"],
                        lighting_mood=["diffused studio glow"],
                        photo_treatment=["soft grain"],
                        mood_keywords=["romantic utility"],
                        visual_motifs=["layered drape"],
                    )
                ],
                style_relation_facets=[
                    StyleRelationFacet(style_id=12, historical_relations=["Victorian romantic linework"])
                ],
            )
        )

        self.assertEqual(output.historical_note_candidates, [])
        self.assertEqual(output.editorial_context_candidates, [])
        self.assertEqual(output.color_poetic_candidates, [])
        self.assertEqual(output.composition_theory_candidates, [])
        self.assertNotIn("ice blue", output.visual_language_points)
        self.assertNotIn("diffused studio glow", output.visual_language_points)
        self.assertIn("romantic utility", output.visual_language_points)
        self.assertIn("layered drape", output.visual_language_points)

    async def test_reasoner_uses_typed_style_advice_and_visual_cards_in_output_signals(self) -> None:
        reasoner = DefaultFashionReasoner()

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="general_advice",
                user_request="Describe the direction more clearly.",
                retrieval_profile="style_focused",
                knowledge_context=KnowledgeContext(
                    providers_used=["style_distilled_provider"],
                    style_advice_cards=[
                        KnowledgeCard(
                            id="advice-card:soft-utility",
                            knowledge_type=KnowledgeType.STYLE_CATALOG,
                            title="Soft utility advice",
                            summary="Ground the look in softened utility tailoring.",
                        )
                    ],
                    style_visual_cards=[
                        KnowledgeCard(
                            id="visual-card:soft-utility",
                            knowledge_type=KnowledgeType.STYLE_CATALOG,
                            title="Soft utility visual",
                            summary="Use chalked light, matte surfaces, and quiet editorial spacing.",
                        )
                    ],
                ),
            )
        )

        self.assertIn(
            "Ground the look in softened utility tailoring.",
            output.style_logic_points,
        )
        self.assertIn(
            "Use chalked light, matte surfaces, and quiet editorial spacing.",
            output.visual_language_points,
        )

    async def test_reasoner_uses_style_history_cards_for_anti_repeat_related_style_selection(self) -> None:
        reasoner = DefaultFashionReasoner()

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="style_exploration",
                user_request="Show another adjacent direction for this look.",
                retrieval_profile="visual_heavy",
                knowledge_context=KnowledgeContext(
                    providers_used=["style_distilled_provider"],
                    style_history_cards=[
                        KnowledgeCard(
                            id="style-history:soft-utility",
                            knowledge_type=KnowledgeType.STYLE_CATALOG,
                            title="Soft Utility",
                            summary="Previously explored softened utility styling.",
                            metadata={
                                "style_cluster": "Soft Utility",
                                "visual_motifs": ["polished chrome"],
                                "source": "style_history",
                            },
                        )
                    ],
                ),
                style_relation_facets=[
                    StyleRelationFacet(
                        style_id=14,
                        related_styles=["Soft Utility", "Gallery Noir"],
                    )
                ],
            )
        )

        self.assertEqual(output.observability["anti_repeat_related_style_selected"], "Gallery Noir")
        self.assertIn("shift toward Gallery Noir.", output.text_response)

    async def test_reasoner_uses_style_history_cards_for_visual_motif_repeat_filtering(self) -> None:
        reasoner = DefaultFashionReasoner()

        output = await reasoner.reason(
            FashionReasoningInput(
                mode="style_exploration",
                user_request="Sharpen the visual language.",
                retrieval_profile="visual_heavy",
                knowledge_context=KnowledgeContext(
                    providers_used=["style_distilled_provider"],
                    style_history_cards=[
                        KnowledgeCard(
                            id="style-history:chrome",
                            knowledge_type=KnowledgeType.STYLE_CATALOG,
                            title="Chrome Minimalism",
                            summary="Previously explored chrome reflections.",
                            metadata={
                                "visual_motifs": ["polished chrome"],
                                "source": "style_history",
                            },
                        )
                    ],
                ),
                style_visual_language_facets=[
                    StyleVisualLanguageFacet(
                        style_id=14,
                        palette=["graphite"],
                        lighting_mood=["gallery haze"],
                        visual_motifs=["polished chrome", "smoked mirror"],
                    )
                ],
            )
        )

        self.assertNotIn("polished chrome", [item.lower() for item in output.visual_language_points])
        self.assertIn("smoked mirror", output.visual_language_points)


class DefaultFashionBriefBuilderTests(unittest.IsolatedAsyncioTestCase):
    async def test_brief_builder_normalizes_reasoning_facets_into_generation_brief(self) -> None:
        reasoner = DefaultFashionReasoner()
        builder = DefaultFashionBriefBuilder()
        reasoning_input = FashionReasoningInput(
            mode="style_exploration",
            user_request="Build a soft futurist look.",
            retrieval_profile="visual_heavy",
            generation_intent=True,
            can_generate_now=True,
            knowledge_context=KnowledgeContext(
                providers_used=["style_ingestion"],
                style_cards=[
                    StyleKnowledgeCard(
                        style_id=12,
                        title="Soft Futurism",
                        summary="Soft technical dressing.",
                    )
                ],
            ),
            style_context=[
                StyleKnowledgeCard(
                    style_id=12,
                    title="Soft Futurism",
                    summary="Soft technical dressing.",
                )
            ],
            style_advice_facets=[
                StyleAdviceFacet(
                    style_id=12,
                    core_style_logic=["soften technical garments with fluid layers"],
                    styling_rules=["balance translucent and silk-matte textures"],
                    statement_pieces=["mesh poet blouse"],
                    status_markers=["silver loafers", "pearl headband"],
                    overlap_context=["bridges utility dressing and romantic eveningwear"],
                    negative_guidance=["avoid hard tactical cosplay"],
                    historical_notes=["space-age minimalism"],
                )
            ],
            style_image_facets=[
                StyleImageFacet(
                    style_id=12,
                    hero_garments=["translucent shell jacket"],
                    secondary_garments=["wide-leg silver trousers"],
                    core_accessories=["chrome headphones"],
                    props=["lucite clutch"],
                    composition_cues=["asymmetric flatlay"],
                    negative_constraints=["no combat props"],
                )
            ],
            style_visual_language_facets=[
                StyleVisualLanguageFacet(
                    style_id=12,
                    palette=["ice blue", "graphite"],
                    lighting_mood=["diffused studio glow"],
                    photo_treatment=["soft bloom"],
                    mood_keywords=["luminous", "polished"],
                    platform_visual_cues=["editorial lookbook framing"],
                )
            ],
            style_relation_facets=[
                StyleRelationFacet(
                    style_id=12,
                    related_styles=["Y2K futurism"],
                    overlap_styles=["soft cyber romantic"],
                    brands=["Paco Rabanne"],
                    platforms=["editorial lookbook"],
                )
            ],
        )

        reasoning_output = await reasoner.reason(reasoning_input)
        brief = await builder.build(
            reasoning_input=reasoning_input,
            reasoning_output=reasoning_output,
        )
        completed_output = reasoning_output.model_copy(
            update={"fashion_brief": brief, "generation_ready": True},
            deep=True,
        )

        self.assertEqual(brief.style_identity, "Soft Futurism")
        self.assertEqual(brief.intent, "style_exploration")
        self.assertEqual(brief.style_direction, "Soft Futurism")
        self.assertEqual(brief.brief_mode, "style_exploration")
        self.assertEqual(brief.hero_garments, ["translucent shell jacket"])
        self.assertEqual(
            brief.anchor_garment,
            {"name": "translucent shell jacket", "source": "hero_garments"},
        )
        self.assertEqual(brief.secondary_garments, ["wide-leg silver trousers", "mesh poet blouse"])
        self.assertEqual(
            brief.garment_list,
            ["translucent shell jacket", "wide-leg silver trousers", "mesh poet blouse"],
        )
        self.assertEqual(brief.palette, ["ice blue", "graphite"])
        self.assertEqual(brief.materials, ["silk", "mesh"])
        self.assertEqual(brief.footwear, ["silver loafers"])
        self.assertEqual(brief.accessories, ["chrome headphones", "pearl headband"])
        self.assertEqual(brief.props, ["lucite clutch"])
        self.assertEqual(brief.photo_treatment, ["soft bloom"])
        self.assertEqual(brief.lighting_mood, ["diffused studio glow"])
        self.assertIn(
            "bridges utility dressing and romantic eveningwear",
            brief.tailoring_logic,
        )
        self.assertIn("luminous", brief.composition_rules)
        self.assertIn("editorial lookbook framing", brief.composition_rules)
        self.assertIn("brand reference: Paco Rabanne", brief.historical_reference)
        self.assertEqual(brief.metadata["mood_keywords"], ["luminous", "polished"])
        self.assertEqual(brief.metadata["platform_visual_cues"], ["editorial lookbook framing"])
        self.assertEqual(brief.metadata["brand_references"], ["Paco Rabanne"])
        self.assertEqual(brief.metadata["platform_references"], ["editorial lookbook"])
        self.assertEqual(
            brief.metadata["overlap_contexts"],
            ["bridges utility dressing and romantic eveningwear"],
        )
        self.assertIn("avoid hard tactical cosplay", brief.negative_constraints)
        self.assertIn("image:12", brief.source_style_facet_ids)
        self.assertTrue(completed_output.has_generation_handoff())
        self.assertEqual(brief.profile_constraints, {})

    async def test_brief_builder_carries_normalized_profile_snapshot_into_handoff_contract(self) -> None:
        reasoner = DefaultFashionReasoner()
        builder = DefaultFashionBriefBuilder()
        reasoning_input = FashionReasoningInput(
            mode="style_exploration",
            user_request="Build a structured androgynous look.",
            retrieval_profile="style_focused",
            generation_intent=True,
            can_generate_now=True,
            profile_context=ProfileContextSnapshot(
                presentation_profile="androgynous",
                fit_preferences=("relaxed",),
                silhouette_preferences=("structured",),
                avoided_items=("heels",),
                legacy_values={"height_cm": 174},
                source="profile_context_service",
            ),
            style_context=[
                StyleKnowledgeCard(
                    style_id=21,
                    title="Structured Androgyny",
                    summary="Clean, elongated tailoring.",
                )
            ],
            style_advice_facets=[
                StyleAdviceFacet(
                    style_id=21,
                    core_style_logic=["keep the lines clean and deliberate"],
                    statement_pieces=["long coat"],
                )
            ],
            style_image_facets=[
                StyleImageFacet(
                    style_id=21,
                    hero_garments=["long coat"],
                    secondary_garments=["wide trousers"],
                )
            ],
        )

        reasoning_output = await reasoner.reason(reasoning_input)
        brief = await builder.build(
            reasoning_input=reasoning_input,
            reasoning_output=reasoning_output,
        )

        self.assertEqual(brief.profile_constraints["presentation_profile"], "androgynous")
        self.assertEqual(brief.profile_constraints["fit_preferences"], ["relaxed"])
        self.assertEqual(brief.profile_constraints["avoided_items"], ["heels"])
        self.assertEqual(brief.profile_context_snapshot["source"], "profile_context_service")
        self.assertEqual(brief.profile_context_snapshot["values"]["height_cm"], 174)

    async def test_brief_builder_uses_profile_facet_weights_for_brief_ordering(self) -> None:
        builder = DefaultFashionBriefBuilder()
        reasoning_input = FashionReasoningInput(
            mode="style_exploration",
            user_request="Build a softer tailoring direction.",
            profile_alignment_applied=True,
            profile_facet_weights={
                "advice:1": 1.0,
                "advice:2": 2.5,
                "image:1": 1.0,
                "image:2": 2.5,
                "visual:1": 1.0,
                "visual:2": 2.5,
                "relation:1": 1.0,
                "relation:2": 2.5,
            },
            style_advice_facets=[
                StyleAdviceFacet(style_id=1, statement_pieces=["black coat"]),
                StyleAdviceFacet(style_id=2, statement_pieces=["ivory blazer"]),
            ],
            style_image_facets=[
                StyleImageFacet(
                    style_id=1,
                    hero_garments=["black coat"],
                    secondary_garments=["charcoal trousers"],
                    core_accessories=["dark belt"],
                    composition_cues=["front pose"],
                ),
                StyleImageFacet(
                    style_id=2,
                    hero_garments=["ivory blazer"],
                    secondary_garments=["cream trousers"],
                    core_accessories=["pearl bag"],
                    composition_cues=["airy diagonal flatlay"],
                ),
            ],
            style_visual_language_facets=[
                StyleVisualLanguageFacet(style_id=1, palette=["black"]),
                StyleVisualLanguageFacet(style_id=2, palette=["ivory"]),
            ],
            style_relation_facets=[
                StyleRelationFacet(style_id=1, related_styles=["Dark Minimal"], overlap_styles=["Industrial Tailoring"]),
                StyleRelationFacet(style_id=2, related_styles=["Soft Tailoring"], overlap_styles=["Romantic Tailoring"]),
            ],
        )
        reasoning_output = FashionReasoningOutput(
            response_type="generation_ready",
            text_response="Let's keep the tailoring soft.",
            style_logic_points=["soft structure"],
            visual_language_points=["ivory"],
            historical_note_candidates=["relaxed elegance"],
            styling_rule_candidates=["keep it fluid"],
            can_offer_visualization=True,
        )

        brief = await builder.build(
            reasoning_input=reasoning_input,
            reasoning_output=reasoning_output,
        )

        self.assertEqual(brief.hero_garments[0], "ivory blazer")
        self.assertEqual(brief.palette[0], "ivory")
        self.assertEqual(brief.style_family, "Romantic Tailoring")
        self.assertEqual(brief.source_style_facet_ids[0], "advice:2")

    async def test_brief_builder_includes_profile_alignment_filters_in_negative_constraints(self) -> None:
        reasoner = DefaultFashionReasoner()
        builder = DefaultFashionBriefBuilder()
        reasoning_input = FashionReasoningInput(
            mode="style_exploration",
            user_request="Build a softer utility look.",
            retrieval_profile="visual_heavy",
            generation_intent=True,
            can_generate_now=True,
            profile_alignment_applied=True,
            profile_alignment_filtered_out=["structured cargo skirt", "moss"],
            knowledge_context=KnowledgeContext(
                providers_used=["style_ingestion"],
                style_cards=[
                    StyleKnowledgeCard(
                        style_id=42,
                        title="Neo Romantic Utility",
                        summary="Utility silhouettes softened by romantic details.",
                    )
                ],
            ),
            style_context=[
                StyleKnowledgeCard(
                    style_id=42,
                    title="Neo Romantic Utility",
                    summary="Utility silhouettes softened by romantic details.",
                )
            ],
            style_advice_facets=[
                StyleAdviceFacet(
                    style_id=42,
                    core_style_logic=["balance hard utility with softer romantic codes"],
                )
            ],
            style_image_facets=[
                StyleImageFacet(
                    style_id=42,
                    hero_garments=["structured cargo skirt"],
                    composition_cues=["editorial three-quarter pose"],
                )
            ],
            style_visual_language_facets=[
                StyleVisualLanguageFacet(
                    style_id=42,
                    palette=["ivory"],
                    lighting_mood=["window-lit softness"],
                )
            ],
        )

        reasoning_output = await reasoner.reason(reasoning_input)
        brief = await builder.build(
            reasoning_input=reasoning_input,
            reasoning_output=reasoning_output,
        )

        self.assertIn(
            "avoid profile-conflicting element: structured cargo skirt",
            brief.negative_constraints,
        )
        self.assertIn(
            "avoid profile-conflicting element: moss",
            brief.negative_constraints,
        )

    async def test_brief_builder_reroutes_to_adjacent_style_and_filters_repeated_visual_motifs(self) -> None:
        reasoner = DefaultFashionReasoner()
        builder = DefaultFashionBriefBuilder()
        reasoning_input = FashionReasoningInput(
            mode="style_exploration",
            user_request="Give me an adjacent direction without repeating the last one.",
            retrieval_profile="visual_heavy",
            generation_intent=True,
            can_generate_now=True,
            knowledge_context=KnowledgeContext(
                providers_used=["style_ingestion"],
                style_cards=[
                    StyleKnowledgeCard(
                        style_id=77,
                        title="Neo Romantic Utility",
                        summary="Utility silhouettes softened by romantic details.",
                    )
                ],
            ),
            style_context=[
                StyleKnowledgeCard(
                    style_id=77,
                    title="Neo Romantic Utility",
                    summary="Utility silhouettes softened by romantic details.",
                )
            ],
            style_history=[
                UsedStyleReference(
                    style_id=8,
                    style_name="Dark Academia",
                    palette=["espresso"],
                    hero_garments=["wool blazer"],
                    visual_motifs=["relaxed layering"],
                )
            ],
            style_advice_facets=[
                StyleAdviceFacet(
                    style_id=77,
                    core_style_logic=["reuse classic academic structure with a softer finish"],
                    styling_rules=["shift the repeated blazer into a lighter outer layer"],
                )
            ],
            style_image_facets=[
                StyleImageFacet(
                    style_id=77,
                    hero_garments=["structured cargo skirt"],
                    composition_cues=["editorial three-quarter pose"],
                )
            ],
            style_visual_language_facets=[
                StyleVisualLanguageFacet(
                    style_id=77,
                    palette=["ivory"],
                    lighting_mood=["window-lit softness"],
                    visual_motifs=["relaxed layering", "antique campus drama"],
                )
            ],
            style_relation_facets=[
                StyleRelationFacet(style_id=77, related_styles=["Romantic Academia"])
            ],
        )

        reasoning_output = await reasoner.reason(reasoning_input)
        brief = await builder.build(
            reasoning_input=reasoning_input,
            reasoning_output=reasoning_output,
        )

        self.assertEqual(brief.style_identity, "Romantic Academia")
        self.assertEqual(brief.style_direction, "Romantic Academia")
        self.assertEqual(brief.visual_motifs, ["antique campus drama"])
        self.assertIn(
            "avoid previously shown visual motif: relaxed layering",
            brief.negative_constraints,
        )

    async def test_brief_builder_uses_style_history_cards_for_anti_repeat_fallbacks(self) -> None:
        reasoner = DefaultFashionReasoner()
        builder = DefaultFashionBriefBuilder()
        reasoning_input = FashionReasoningInput(
            mode="style_exploration",
            user_request="Show another adjacent direction for this look.",
            retrieval_profile="visual_heavy",
            knowledge_context=KnowledgeContext(
                providers_used=["style_distilled_provider"],
                style_history_cards=[
                    KnowledgeCard(
                        id="style-history:soft-utility",
                        knowledge_type=KnowledgeType.STYLE_CATALOG,
                        title="Soft Utility",
                        summary="Previously explored softened utility styling.",
                        metadata={
                            "style_cluster": "Soft Utility",
                            "visual_motifs": ["polished chrome"],
                            "source": "style_history",
                        },
                    )
                ],
            ),
            style_relation_facets=[
                StyleRelationFacet(
                    style_id=14,
                    related_styles=["Soft Utility", "Gallery Noir"],
                )
            ],
            style_visual_language_facets=[
                StyleVisualLanguageFacet(
                    style_id=14,
                    palette=["graphite"],
                    visual_motifs=["polished chrome", "smoked mirror"],
                )
            ],
        )

        reasoning_output = await reasoner.reason(reasoning_input)
        brief = await builder.build(
            reasoning_input=reasoning_input,
            reasoning_output=reasoning_output,
        )

        self.assertEqual(reasoning_output.observability["anti_repeat_related_style_selected"], "Gallery Noir")
        self.assertEqual(brief.style_direction, "Gallery Noir")
        self.assertEqual(brief.style_identity, "Gallery Noir")
        self.assertNotIn("polished chrome", [item.lower() for item in brief.visual_motifs])
        self.assertIn("smoked mirror", brief.visual_motifs)


class DefaultFashionReasoningPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_runs_assembler_alignment_reasoner_and_brief_builder(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=ProfileAlignedFashionReasoningContextAssembler(
                context_assembler=DefaultFashionReasoningContextAssembler(
                    knowledge_provider=FakeReasoningKnowledgeProvider(),
                    style_facet_provider=FakeStyleFacetProvider(),
                ),
                alignment_service=DefaultProfileStyleAlignmentService(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a softer utility direction.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=ProfileContextSnapshot(
                present=True,
                values={"preferred_palette": "ivory"},
            ),
            retrieval_profile=None,
        )

        self.assertEqual(output.response_type, "generation_ready")
        self.assertTrue(output.has_generation_handoff())
        self.assertIsNotNone(output.fashion_brief)
        self.assertEqual(output.fashion_brief.style_identity, "Neo Romantic Utility")
        self.assertEqual(output.fashion_brief.palette[0], "ivory")
        self.assertIn("image:42", output.fashion_brief.source_style_facet_ids)
        self.assertTrue(output.observability["fashion_brief_built"])
        self.assertTrue(output.observability["generation_ready"])
        self.assertEqual(
            output.observability["profile_alignment_boosted_categories"],
            ["visual_language"],
        )
        self.assertEqual(output.observability["profile_alignment_removed_item_types"], [])
        self.assertEqual(output.observability["profile_clarification_decision"], "skipped")
        self.assertEqual(output.observability["routing_mode"], "style_exploration")
        self.assertEqual(output.observability["retrieval_profile"], "visual_heavy")
        self.assertEqual(output.observability["used_providers"], ["fake_style_provider"])
        self.assertEqual(output.observability["style_facets_count"], 4)
        self.assertTrue(output.observability["profile_alignment_applied"])
        self.assertEqual(output.observability["profile_alignment_boosted_categories_count"], 1)
        self.assertEqual(output.observability["profile_alignment_removed_item_types_count"], 0)
        self.assertGreaterEqual(output.observability["style_image_facets_count"], 1)
        self.assertTrue(output.observability["cta_offered"])
        self.assertGreater(output.observability["cta_confidence_score"], 0.0)
        self.assertTrue(output.observability["profile_signals_sufficient"])
        self.assertFalse(output.observability["reasoning_is_mostly_advisory"])
        self.assertEqual(output.observability["style_logic_points_count"], len(output.style_logic_points))
        self.assertEqual(
            output.observability["visual_language_points_count"],
            len(output.visual_language_points),
        )
        self.assertEqual(
            output.observability["historical_note_candidates_count"],
            len(output.historical_note_candidates),
        )
        self.assertEqual(
            output.observability["styling_rule_candidates_count"],
            len(output.styling_rule_candidates),
        )
        self.assertEqual(output.reasoning_metadata.routing_mode, "style_exploration")
        self.assertEqual(output.reasoning_metadata.retrieval_profile, "visual_heavy")
        self.assertEqual(output.reasoning_metadata.used_providers, ["fake_style_provider"])
        self.assertEqual(output.reasoning_metadata.style_facets_count, 4)
        self.assertEqual(output.reasoning_metadata.style_logic_points_count, len(output.style_logic_points))
        self.assertEqual(
            output.reasoning_metadata.visual_language_points_count,
            len(output.visual_language_points),
        )
        self.assertEqual(
            output.reasoning_metadata.historical_note_candidates_count,
            len(output.historical_note_candidates),
        )
        self.assertEqual(
            output.reasoning_metadata.styling_rule_candidates_count,
            len(output.styling_rule_candidates),
        )
        self.assertTrue(output.reasoning_metadata.profile_alignment_applied)
        self.assertTrue(output.reasoning_metadata.fashion_brief_built)
        self.assertTrue(output.reasoning_metadata.generation_ready)
        self.assertEqual(output.fashion_brief.profile_constraints["color_preferences"], ["ivory"])

    async def test_pipeline_carries_profile_alignment_filters_into_brief_negative_constraints(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=ProfileAlignedFashionReasoningContextAssembler(
                context_assembler=DefaultFashionReasoningContextAssembler(
                    knowledge_provider=FakeReasoningKnowledgeProvider(),
                    style_facet_provider=FakeStyleFacetProvider(),
                ),
                alignment_service=DefaultProfileStyleAlignmentService(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a softer utility direction.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=ProfileContextSnapshot(
                present=True,
                values={"excluded_garments": ["structured cargo skirt"], "preferred_palette": "ivory"},
            ),
            retrieval_profile=None,
        )

        self.assertTrue(output.has_generation_handoff())
        assert output.fashion_brief is not None
        self.assertIn(
            "avoid profile-conflicting element: structured cargo skirt",
            output.fashion_brief.negative_constraints,
        )

    async def test_pipeline_supports_style_focused_advice_without_generation_handoff(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=AdviceOnlyStyleFacetProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.GENERAL_ADVICE,
                retrieval_profile="style_focused",
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Explain a softer heritage direction for everyday wear.",
                can_generate_now=True,
                current_style_name="Soft Retro Prep",
            ),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertEqual(output.response_type, "text")
        self.assertFalse(output.requires_clarification())
        self.assertFalse(output.can_offer_visualization)
        self.assertFalse(output.has_generation_handoff())
        self.assertIsNone(output.fashion_brief)
        self.assertIn("keep the structure polished but relaxed for real wear", output.style_logic_points)
        self.assertIn("modern heritage dressing", output.historical_note_candidates)
        self.assertEqual(output.reasoning_metadata.retrieval_profile, "style_focused")
        self.assertFalse(output.observability["fashion_brief_built"])
        self.assertFalse(output.observability["cta_offered"])
        self.assertEqual(output.observability["cta_decision_reason"], "insufficient_image_context")
        self.assertEqual(
            output.observability["cta_blocked_reasons"],
            ["insufficient_image_context", "missing_visual_language"],
        )
        self.assertEqual(output.observability["cta_confidence_score"], 0.0)
        self.assertFalse(output.observability["profile_signals_sufficient"])
        self.assertTrue(output.observability["reasoning_is_mostly_advisory"])
        self.assertEqual(output.observability["style_logic_points_count"], len(output.style_logic_points))
        self.assertEqual(output.observability["visual_language_points_count"], 0)
        self.assertEqual(
            output.observability["historical_note_candidates_count"],
            len(output.historical_note_candidates),
        )
        self.assertEqual(
            output.observability["styling_rule_candidates_count"],
            len(output.styling_rule_candidates),
        )
        self.assertEqual(output.reasoning_metadata.style_logic_points_count, len(output.style_logic_points))
        self.assertEqual(output.reasoning_metadata.visual_language_points_count, 0)
        self.assertEqual(output.observability["generation_blocked_reason"], "visualization_not_offered")

    async def test_pipeline_supports_occasion_outfit_advice_without_generation_handoff(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=AdviceOnlyStyleFacetProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.OCCASION_OUTFIT,
                retrieval_profile="occasion_focused",
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="I need an occasion outfit idea for a spring dinner.",
                active_slots={"occasion": "spring dinner", "weather": "mild evening"},
                can_generate_now=True,
                current_style_name="Soft Retro Prep",
            ),
            profile_context=ProfileContextSnapshot(
                present=True,
                values={"fit": "relaxed"},
            ),
            retrieval_profile=None,
        )

        self.assertEqual(output.response_type, "text")
        self.assertFalse(output.requires_clarification())
        self.assertFalse(output.can_offer_visualization)
        self.assertFalse(output.has_generation_handoff())
        self.assertIsNone(output.fashion_brief)
        self.assertIn("keep the structure polished but relaxed for real wear", output.style_logic_points)
        self.assertEqual(output.reasoning_metadata.retrieval_profile, "occasion_focused")
        self.assertFalse(output.observability["clarification_required"])
        self.assertFalse(output.observability["fashion_brief_built"])

    async def test_pipeline_carries_occasion_context_and_visual_preset_into_generation_brief(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=FakeStyleFacetProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.OCCASION_OUTFIT,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Build an elevated dinner look I can visualize.",
                active_slots={
                    "occasion": "gallery dinner",
                    "weather": "mild evening",
                    "time_of_day": "evening",
                    "season": "spring",
                },
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
                diversity_constraints=DiversityConstraints(
                    suggested_visual_preset="airy_catalog",
                ),
            ),
            profile_context=ProfileContextSnapshot(
                present=True,
                values={
                    "fit": "relaxed",
                    "dress_code": "smart casual",
                    "desired_impression": "elegant",
                },
            ),
            retrieval_profile=None,
        )

        self.assertEqual(output.response_type, "generation_ready")
        self.assertTrue(output.has_generation_handoff())
        assert output.fashion_brief is not None
        self.assertEqual(
            output.fashion_brief.occasion_context,
            {
                "event_type": "gallery dinner",
                "weather_context": "mild evening",
                "time_of_day": "evening",
                "season": "spring",
                "dress_code": "smart casual",
                "desired_impression": "elegant",
            },
        )
        self.assertEqual(
            output.fashion_brief.anchor_garment,
            {"name": "structured cargo skirt", "source": "hero_garments"},
        )
        self.assertEqual(output.fashion_brief.visual_preset, "airy_catalog")

    async def test_pipeline_returns_visual_offer_when_visual_context_is_strong_but_generation_is_not_requested(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=FakeStyleFacetProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                retrieval_profile="visual_heavy",
                generation_intent=False,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a softer utility direction first, without generating yet.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertEqual(output.response_type, "visual_offer")
        self.assertTrue(output.can_offer_visualization)
        self.assertFalse(output.requires_clarification())
        self.assertFalse(output.has_generation_handoff())
        self.assertIsNotNone(output.fashion_brief)
        self.assertEqual(output.suggested_cta, "Visualize this direction")
        self.assertEqual(output.image_cta_candidates[0].required_generation_trigger, "offer_visualization")
        self.assertTrue(output.observability["fashion_brief_built"])
        self.assertTrue(output.observability["cta_offered"])
        self.assertEqual(
            output.observability["cta_decision_reason"],
            "image_context_and_visual_language_sufficient",
        )
        self.assertEqual(output.observability["cta_blocked_reasons"], [])
        self.assertFalse(output.observability["generation_ready"])
        self.assertFalse(output.observability["visual_intent_signal_present"])
        self.assertEqual(output.observability["generation_blocked_reason"], "generation_not_ready")

    async def test_pipeline_uses_generation_intent_as_visual_intent_signal_for_handoff_branching(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=FakeStyleFacetProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )
        base_session_state = SessionStateSnapshot(
            user_request="Show a softer utility direction.",
            can_generate_now=True,
            current_style_name="Neo Romantic Utility",
        )

        visual_offer_output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                retrieval_profile="visual_heavy",
                generation_intent=False,
                requires_style_retrieval=True,
            ),
            session_state=base_session_state,
            profile_context=None,
            retrieval_profile=None,
        )
        generation_ready_output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                retrieval_profile="visual_heavy",
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=base_session_state,
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertEqual(visual_offer_output.response_type, "visual_offer")
        self.assertEqual(generation_ready_output.response_type, "generation_ready")
        self.assertFalse(visual_offer_output.observability["visual_intent_signal_present"])
        self.assertTrue(generation_ready_output.observability["visual_intent_signal_present"])
        self.assertFalse(visual_offer_output.generation_ready)
        self.assertTrue(generation_ready_output.generation_ready)
        self.assertFalse(visual_offer_output.has_generation_handoff())
        self.assertTrue(generation_ready_output.has_generation_handoff())
        self.assertEqual(visual_offer_output.style_logic_points, generation_ready_output.style_logic_points)
        self.assertEqual(
            visual_offer_output.visual_language_points,
            generation_ready_output.visual_language_points,
        )
        assert visual_offer_output.fashion_brief is not None
        assert generation_ready_output.fashion_brief is not None
        self.assertEqual(
            visual_offer_output.fashion_brief.style_identity,
            generation_ready_output.fashion_brief.style_identity,
        )
        self.assertEqual(
            visual_offer_output.fashion_brief.garment_list,
            generation_ready_output.fashion_brief.garment_list,
        )
        self.assertEqual(
            visual_offer_output.fashion_brief.palette,
            generation_ready_output.fashion_brief.palette,
        )
        self.assertEqual(
            visual_offer_output.fashion_brief.composition_rules,
            generation_ready_output.fashion_brief.composition_rules,
        )

    async def test_pipeline_uses_explicit_visual_intent_signal_to_adjust_visual_offer_confidence(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=FakeStyleFacetProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        advice_only_output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                retrieval_profile="visual_heavy",
                generation_intent=False,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a softer utility direction first.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
                visual_intent_signal="advice_only",
            ),
            profile_context=None,
            retrieval_profile=None,
        )
        open_visual_output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                retrieval_profile="visual_heavy",
                generation_intent=False,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a softer utility direction first.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
                visual_intent_signal="open_to_visualization",
            ),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertEqual(advice_only_output.response_type, "visual_offer")
        self.assertEqual(open_visual_output.response_type, "visual_offer")
        self.assertTrue(advice_only_output.observability["visual_intent_signal_present"])
        self.assertTrue(open_visual_output.observability["visual_intent_signal_present"])
        self.assertTrue(advice_only_output.observability["reasoning_is_mostly_advisory"])
        self.assertFalse(open_visual_output.observability["reasoning_is_mostly_advisory"])
        self.assertLess(
            advice_only_output.observability["cta_confidence_score"],
            open_visual_output.observability["cta_confidence_score"],
        )

    async def test_pipeline_keeps_clarification_without_brief_handoff(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(mode=RoutingMode.OCCASION_OUTFIT),
            session_state=SessionStateSnapshot(user_request="Need an outfit."),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertTrue(output.requires_clarification())
        self.assertIsNone(output.fashion_brief)
        self.assertFalse(output.has_generation_handoff())
        self.assertTrue(output.observability["clarification_required"])
        self.assertFalse(output.observability["fashion_brief_built"])
        self.assertFalse(output.observability["cta_offered"])
        self.assertEqual(output.observability["cta_decision_reason"], "clarification_required")
        self.assertEqual(output.observability["cta_blocked_reasons"], ["clarification_required"])
        self.assertEqual(output.observability["style_logic_points_count"], 0)
        self.assertEqual(output.observability["visual_language_points_count"], 0)
        self.assertEqual(output.observability["historical_note_candidates_count"], 0)
        self.assertEqual(output.observability["styling_rule_candidates_count"], 0)
        self.assertEqual(output.reasoning_metadata.style_logic_points_count, 0)
        self.assertEqual(output.reasoning_metadata.visual_language_points_count, 0)
        self.assertFalse(output.observability["generation_ready"])
        self.assertEqual(output.observability["generation_blocked_reason"], "clarification_required")

    async def test_pipeline_requests_silhouette_preference_before_occasion_brief(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=AdviceOnlyStyleFacetProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.OCCASION_OUTFIT,
                retrieval_profile="occasion_focused",
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="I need an occasion outfit idea for a spring dinner.",
                active_slots={"occasion": "spring dinner", "weather": "mild evening"},
                can_generate_now=True,
                current_style_name="Soft Retro Prep",
            ),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertTrue(output.requires_clarification())
        self.assertEqual(
            output.clarification_question,
            "Do you prefer a relaxed, fitted, or oversized silhouette for this look?",
        )
        self.assertIsNone(output.fashion_brief)
        self.assertFalse(output.has_generation_handoff())
        self.assertTrue(output.observability["clarification_required"])
        self.assertFalse(output.observability["fashion_brief_built"])

    async def test_pipeline_requests_visual_intent_before_visual_branch_when_required(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=FakeStyleFacetProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.OCCASION_OUTFIT,
                retrieval_profile="occasion_focused",
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="I need an occasion outfit idea for a spring dinner.",
                active_slots={"occasion": "spring dinner", "weather": "mild evening"},
                visual_intent_required=True,
                can_generate_now=True,
                current_style_name="Soft Retro Prep",
            ),
            profile_context=ProfileContextSnapshot(
                values={"silhouette": "relaxed"},
                present=True,
            ),
            retrieval_profile=None,
        )

        self.assertTrue(output.requires_clarification())
        self.assertEqual(
            output.clarification_question,
            "Should I keep this as text advice, or shape it toward a visualizable outfit direction?",
        )
        self.assertIsNone(output.fashion_brief)
        self.assertFalse(output.has_generation_handoff())
        self.assertTrue(output.observability["clarification_required"])
        self.assertTrue(output.observability["visual_intent_required"])
        self.assertFalse(output.observability["visual_intent_signal_present"])

    async def test_pipeline_applies_anti_repeat_reroute_constraints_to_brief_and_observability(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=RepeatHeavyStyleFacetProvider(),
                style_history_provider=FakeStyleHistoryProvider(),
                diversity_constraints_provider=FakeDiversityConstraintsProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Give me an adjacent academy direction without repeating the last one.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertTrue(output.has_generation_handoff())
        self.assertIsNotNone(output.fashion_brief)
        self.assertEqual(output.fashion_brief.style_identity, "Romantic Academia")
        self.assertEqual(output.fashion_brief.hero_garments, ["structured cargo skirt"])
        self.assertEqual(output.fashion_brief.palette, ["ivory"])
        self.assertEqual(output.fashion_brief.visual_motifs, ["antique campus drama"])
        self.assertNotIn("wool blazer", output.fashion_brief.garment_list)
        self.assertNotIn("espresso", output.fashion_brief.palette)
        self.assertNotIn("espresso", output.fashion_brief.color_logic)
        self.assertNotIn("espresso", output.visual_language_points)
        self.assertNotIn("relaxed layering", output.visual_language_points)
        self.assertIn("avoid recently used palette: espresso", output.fashion_brief.negative_constraints)
        self.assertIn("avoid recently used hero garment: wool blazer", output.fashion_brief.negative_constraints)
        self.assertIn(
            "avoid previously shown visual motif: relaxed layering",
            output.fashion_brief.negative_constraints,
        )
        self.assertEqual(output.fashion_brief.diversity_constraints["avoid_palette"], ["espresso"])
        self.assertEqual(output.observability["style_history_count"], 1)
        self.assertEqual(output.observability["style_history_cards"], 1)
        self.assertEqual(output.observability["diversity_constraints_present"], 1)
        self.assertEqual(output.observability["anti_repeat_related_style_selected"], "Romantic Academia")
        self.assertEqual(output.observability["anti_repeat_visual_motifs_avoided_count"], 1)

    async def test_pipeline_keeps_text_response_and_fashion_brief_consistent_for_anti_repeat_reroute(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=RepeatHeavyStyleFacetProvider(),
                style_history_provider=FakeStyleHistoryProvider(),
                diversity_constraints_provider=FakeDiversityConstraintsProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Give me an adjacent academy direction without repeating the last one.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertTrue(output.has_generation_handoff())
        assert output.fashion_brief is not None
        self.assertEqual(output.fashion_brief.style_identity, "Romantic Academia")
        self.assertIn(output.fashion_brief.style_identity, output.text_response)
        self.assertIn(output.fashion_brief.palette[0], output.text_response)
        self.assertIn(output.style_logic_points[0], output.text_response)

    async def test_pipeline_keeps_legacy_style_context_while_richer_facets_expand_output(self) -> None:
        legacy_pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )
        richer_pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=FakeStyleFacetProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )
        routing_decision = RoutingDecision(
            mode=RoutingMode.STYLE_EXPLORATION,
            generation_intent=True,
            requires_style_retrieval=True,
        )
        session_state = SessionStateSnapshot(
            user_request="Show a softer utility direction.",
            can_generate_now=True,
            current_style_name="Neo Romantic Utility",
        )

        legacy_output = await legacy_pipeline.run(
            routing_decision=routing_decision,
            session_state=session_state,
            profile_context=None,
            retrieval_profile=None,
        )
        richer_output = await richer_pipeline.run(
            routing_decision=routing_decision,
            session_state=session_state,
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertEqual(legacy_output.response_type, "text")
        self.assertIn("Utility silhouettes softened by romantic details.", legacy_output.style_logic_points)
        self.assertFalse(legacy_output.can_offer_visualization)
        self.assertIsNone(legacy_output.fashion_brief)
        self.assertFalse(legacy_output.observability["fashion_brief_built"])
        self.assertEqual(legacy_output.reasoning_metadata.style_facets_count, 0)
        self.assertEqual(legacy_output.reasoning_metadata.used_providers, ["fake_style_provider"])

        self.assertEqual(richer_output.response_type, "generation_ready")
        self.assertTrue(richer_output.has_generation_handoff())
        self.assertGreater(richer_output.reasoning_metadata.style_facets_count, 0)
        self.assertIn("balance hard utility with softer romantic codes", richer_output.style_logic_points)
        self.assertIn("moss", richer_output.visual_language_points)
        self.assertIsNotNone(richer_output.fashion_brief)
        self.assertEqual(richer_output.fashion_brief.style_identity, "Neo Romantic Utility")
        self.assertTrue(richer_output.observability["fashion_brief_built"])

    async def test_pipeline_uses_semantic_fragments_as_downstream_reasoning_signals(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                semantic_fragment_provider=SemanticOnlyFragmentProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a softer utility direction from distilled fragments.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertEqual(output.response_type, "generation_ready")
        self.assertTrue(output.has_generation_handoff())
        self.assertIn("Use softened utility structure as the main styling logic.", output.style_logic_points)
        self.assertIn("ivory palette with window-lit softness", output.visual_language_points)
        self.assertIn("editorial three-quarter composition with negative space", output.visual_language_points)
        self.assertIn("adjacent to Romantic Academia", output.historical_note_candidates)
        self.assertEqual(output.reasoning_metadata.style_semantic_fragments_count, 4)
        self.assertTrue(output.observability["fashion_brief_built"])
        self.assertIsNotNone(output.fashion_brief)
        self.assertEqual(output.fashion_brief.style_identity, "Neo Romantic Utility")
        self.assertIn("ivory palette with window-lit softness", output.fashion_brief.color_logic)
        self.assertIn(
            "editorial three-quarter composition with negative space",
            output.fashion_brief.composition_rules,
        )

    async def test_pipeline_carries_knowledge_layer_history_into_fashion_brief(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=HistoricalKnowledgeProvider(),
                style_facet_provider=FakeStyleFacetProvider(),
                knowledge_runtime_flags=KnowledgeRuntimeFlags(
                    use_historical_context=True,
                    use_editorial_knowledge=True,
                    use_color_poetics=True,
                ),
            ),
            reasoner=DefaultFashionReasoner(
                knowledge_runtime_flags=KnowledgeRuntimeFlags(
                    use_historical_context=True,
                    use_editorial_knowledge=True,
                )
            ),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a romantic utility direction with historical texture.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=None,
            retrieval_profile=None,
        )

        self.assertTrue(output.has_generation_handoff())
        assert output.fashion_brief is not None
        self.assertIn(
            "Belle Epoque evening references and elongated linework.",
            output.fashion_brief.historical_reference,
        )
        self.assertIn(
            "Editorial revival through softened romantic utility framing.",
            output.fashion_brief.historical_reference,
        )

    async def test_pipeline_can_reason_from_central_knowledge_context_layer(self) -> None:
        knowledge_context_assembler = FakeKnowledgeContextAssembler(build_rich_knowledge_context())
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=ProfileAlignedFashionReasoningContextAssembler(
                context_assembler=DefaultFashionReasoningContextAssembler(
                    knowledge_context_assembler=knowledge_context_assembler,
                    knowledge_runtime_flags=KnowledgeRuntimeFlags(
                        use_historical_context=True,
                        use_editorial_knowledge=True,
                        use_color_poetics=True,
                    ),
                ),
                alignment_service=DefaultProfileStyleAlignmentService(),
            ),
            reasoner=DefaultFashionReasoner(
                knowledge_runtime_flags=KnowledgeRuntimeFlags(
                    use_historical_context=True,
                    use_editorial_knowledge=True,
                    use_color_poetics=True,
                )
            ),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a romantic utility direction grounded in knowledge layers.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=ProfileContextSnapshot(
                values={"preferred_palette": "ivory"},
                present=True,
            ),
            retrieval_profile=None,
        )

        assert knowledge_context_assembler.query is not None
        self.assertEqual(
            knowledge_context_assembler.query.profile_context["color_preferences"],
            ["ivory"],
        )
        self.assertEqual(output.reasoning_metadata.used_providers, ["style_ingestion", "fashion_historian"])
        self.assertIn(
            "balance structure and softness through romantic detailing",
            output.style_logic_points,
        )
        self.assertIn("moss", output.visual_language_points)
        self.assertIn(
            "Belle Epoque evening references and elongated linework.",
            output.historical_note_candidates,
        )
        self.assertIn(
            "Editorial revival through softened romantic utility framing.",
            output.editorial_context_candidates,
        )
        self.assertIn("keep the waist defined", output.styling_rule_candidates)
        self.assertIn("moss", output.color_poetic_candidates)
        self.assertIn(
            "editorial three-quarter pose",
            output.composition_theory_candidates,
        )
        self.assertTrue(output.observability["fashion_brief_built"])
        self.assertTrue(output.observability["profile_alignment_applied"])
        self.assertTrue(output.has_generation_handoff())
        assert output.fashion_brief is not None
        self.assertEqual(output.fashion_brief.style_identity, "Neo Romantic Utility")
        self.assertEqual(output.fashion_brief.profile_constraints["color_preferences"], ["ivory"])
        self.assertEqual(output.observability["knowledge_query_mode"], "style_exploration")
        self.assertEqual(output.observability["knowledge_retrieval_profile"], "visual_heavy")
        self.assertEqual(output.observability["knowledge_provider_count"], 2)
        self.assertEqual(
            output.observability["knowledge_providers_used"],
            ["style_ingestion", "fashion_historian"],
        )
        self.assertEqual(
            output.observability["knowledge_cards_per_provider"]["style_ingestion"],
            4,
        )
        self.assertEqual(
            output.observability["knowledge_cards_per_provider"]["fashion_historian"],
            2,
        )
        self.assertEqual(output.observability["knowledge_empty_providers"], [])
        self.assertIn(
            "style_visual_language",
            output.observability["style_provider_knowledge_types"],
        )
        self.assertIn(
            "style-facet-projector.v1",
            output.observability["style_provider_projection_versions"],
        )

    async def test_pipeline_respects_knowledge_runtime_flags_in_central_knowledge_path(self) -> None:
        knowledge_context_assembler = FakeKnowledgeContextAssembler(build_rich_knowledge_context())
        runtime_flags = KnowledgeRuntimeFlags(
            use_historical_context=False,
            use_editorial_knowledge=False,
            use_color_poetics=False,
        )
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=ProfileAlignedFashionReasoningContextAssembler(
                context_assembler=DefaultFashionReasoningContextAssembler(
                    knowledge_context_assembler=knowledge_context_assembler,
                    knowledge_runtime_flags=runtime_flags,
                ),
                alignment_service=DefaultProfileStyleAlignmentService(),
            ),
            reasoner=DefaultFashionReasoner(
                knowledge_runtime_flags=runtime_flags,
            ),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a romantic utility direction grounded in knowledge layers.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=ProfileContextSnapshot(
                values={"color_preferences": ["ivory"]},
                present=True,
            ),
            retrieval_profile=None,
        )

        assert knowledge_context_assembler.query is not None
        self.assertFalse(knowledge_context_assembler.query.need_historical_knowledge)
        self.assertFalse(knowledge_context_assembler.query.need_color_poetics)
        self.assertEqual(output.reasoning_metadata.used_providers, ["style_ingestion", "fashion_historian"])
        self.assertEqual(output.historical_note_candidates, [])
        self.assertNotIn("moss", output.visual_language_points)
        self.assertNotIn("window-lit softness", output.visual_language_points)
        self.assertIn("editorial calm", output.visual_language_points)
        self.assertTrue(output.has_generation_handoff())
        assert output.fashion_brief is not None
        self.assertEqual(output.fashion_brief.historical_reference, [])

    async def test_pipeline_prefers_runtime_settings_provider_over_static_flags_in_central_knowledge_path(self) -> None:
        knowledge_context_assembler = FakeKnowledgeContextAssembler(build_rich_knowledge_context())
        runtime_settings_provider = FakeKnowledgeRuntimeSettingsProvider(
            KnowledgeRuntimeFlags(
                use_historical_context=False,
                use_editorial_knowledge=False,
                use_color_poetics=False,
            )
        )
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=ProfileAlignedFashionReasoningContextAssembler(
                context_assembler=DefaultFashionReasoningContextAssembler(
                    knowledge_context_assembler=knowledge_context_assembler,
                    knowledge_runtime_flags=KnowledgeRuntimeFlags(
                        use_historical_context=True,
                        use_editorial_knowledge=True,
                        use_color_poetics=True,
                    ),
                    knowledge_runtime_settings_provider=runtime_settings_provider,
                ),
                alignment_service=DefaultProfileStyleAlignmentService(),
            ),
            reasoner=DefaultFashionReasoner(
                knowledge_runtime_flags=KnowledgeRuntimeFlags(
                    use_historical_context=True,
                    use_editorial_knowledge=True,
                    use_color_poetics=True,
                ),
                knowledge_runtime_settings_provider=runtime_settings_provider,
            ),
            brief_builder=DefaultFashionBriefBuilder(),
        )

        output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a romantic utility direction grounded in knowledge layers.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=ProfileContextSnapshot(
                values={"color_preferences": ["ivory"]},
                present=True,
            ),
            retrieval_profile=None,
        )

        assert knowledge_context_assembler.query is not None
        self.assertFalse(knowledge_context_assembler.query.need_historical_knowledge)
        self.assertFalse(knowledge_context_assembler.query.need_color_poetics)
        self.assertEqual(output.historical_note_candidates, [])
        self.assertEqual(output.editorial_context_candidates, [])
        self.assertEqual(output.color_poetic_candidates, [])
        self.assertEqual(output.composition_theory_candidates, [])
        self.assertNotIn("moss", output.visual_language_points)
        self.assertNotIn("window-lit softness", output.visual_language_points)


class DefaultReasoningOutputMapperTests(unittest.IsolatedAsyncioTestCase):
    async def test_mapper_splits_reasoning_output_for_voice_and_generation_handoff(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=DefaultFashionReasoningContextAssembler(
                knowledge_provider=FakeReasoningKnowledgeProvider(),
                style_facet_provider=FakeStyleFacetProvider(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )
        mapper = DefaultReasoningOutputMapper()

        reasoning_output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a softer utility direction.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=None,
            retrieval_profile=None,
        )
        payload = await mapper.to_presentation(reasoning_output)

        self.assertIsInstance(payload, FashionReasoningPresentationPayload)
        self.assertIsInstance(payload.voice, VoiceLayerReasoningPayload)
        self.assertIsInstance(payload.generation, GenerationHandoffPayload)
        self.assertIn(reasoning_output.text_response, payload.voice.draft_text)
        self.assertEqual(payload.voice.tone_profile, "smart_stylist_with_historian_and_color_poetics_rich_but_controlled")
        self.assertEqual(payload.voice.voice_layers_used, ["stylist", "historian", "color_poetics"])
        self.assertTrue(payload.voice.includes_historical_note)
        self.assertTrue(payload.voice.includes_color_poetics)
        self.assertEqual(payload.voice.observability["voice_mode"], "style_exploration")
        self.assertEqual(payload.voice.observability["voice_response_type"], "brief_ready_for_generation")
        self.assertEqual(payload.voice.observability["voice_desired_depth"], "deep")
        self.assertEqual(payload.voice.observability["voice_knowledge_density"], "high")
        self.assertEqual(payload.voice.observability["voice_brevity_level"], "deep")
        self.assertEqual(payload.voice.observability["voice_cta_style"], "editorial_soft")
        self.assertTrue(payload.voice.observability["voice_cta_present"])
        self.assertGreater(payload.voice.observability["voice_text_length"], 0)
        self.assertEqual(payload.voice.style_logic_points, reasoning_output.style_logic_points)
        self.assertEqual(
            payload.voice.visual_language_points,
            reasoning_output.visual_language_points,
        )
        self.assertEqual(
            payload.voice.historical_note_candidates,
            reasoning_output.historical_note_candidates,
        )
        self.assertEqual(
            payload.voice.styling_rule_candidates,
            reasoning_output.styling_rule_candidates,
        )
        self.assertEqual(
            payload.voice.editorial_context_candidates,
            reasoning_output.editorial_context_candidates,
        )
        self.assertEqual(
            payload.voice.color_poetic_candidates,
            reasoning_output.color_poetic_candidates,
        )
        self.assertEqual(
            payload.voice.composition_theory_candidates,
            reasoning_output.composition_theory_candidates,
        )
        self.assertTrue(payload.generation.generation_ready)
        self.assertIsNotNone(payload.generation.fashion_brief)
        self.assertIsNone(payload.generation.blocked_reason)
        self.assertEqual(payload.observability["generation_ready"], True)

    async def test_mapper_keeps_voice_text_and_fashion_brief_consistent(self) -> None:
        pipeline = DefaultFashionReasoningPipeline(
            context_assembler=ProfileAlignedFashionReasoningContextAssembler(
                context_assembler=DefaultFashionReasoningContextAssembler(
                    knowledge_provider=FakeReasoningKnowledgeProvider(),
                    style_facet_provider=FakeStyleFacetProvider(),
                ),
                alignment_service=DefaultProfileStyleAlignmentService(),
            ),
            reasoner=DefaultFashionReasoner(),
            brief_builder=DefaultFashionBriefBuilder(),
        )
        mapper = DefaultReasoningOutputMapper()

        reasoning_output = await pipeline.run(
            routing_decision=RoutingDecision(
                mode=RoutingMode.STYLE_EXPLORATION,
                generation_intent=True,
                requires_style_retrieval=True,
            ),
            session_state=SessionStateSnapshot(
                user_request="Show a softer utility direction.",
                can_generate_now=True,
                current_style_name="Neo Romantic Utility",
            ),
            profile_context=ProfileContextSnapshot(
                present=True,
                values={"preferred_palette": "ivory"},
            ),
            retrieval_profile=None,
        )
        payload = await mapper.to_presentation(reasoning_output)

        assert payload.generation.fashion_brief is not None
        fashion_brief = payload.generation.fashion_brief
        self.assertEqual(fashion_brief.style_identity, "Neo Romantic Utility")
        self.assertEqual(fashion_brief.palette[0], "ivory")
        self.assertEqual(payload.voice.visual_language_points[0], fashion_brief.palette[0])
        self.assertIn(payload.voice.style_logic_points[0], payload.voice.draft_text)
        self.assertIn(fashion_brief.palette[0], payload.voice.draft_text)
        self.assertEqual(payload.generation.generation_ready, reasoning_output.generation_ready)
        self.assertEqual(payload.generation.fashion_brief.content_hash(), fashion_brief.content_hash())

    async def test_mapper_keeps_clarification_as_voice_payload_without_generation_brief(self) -> None:
        mapper = DefaultReasoningOutputMapper()
        reasoner = DefaultFashionReasoner()
        reasoning_output = await reasoner.reason(
            FashionReasoningInput(
                mode="occasion_outfit",
                user_request="Need an outfit.",
            )
        )

        payload = await mapper.to_presentation(reasoning_output)

        self.assertEqual(payload.voice.response_type, "clarification")
        self.assertEqual(payload.voice.clarification_question, reasoning_output.clarification_question)
        self.assertFalse(payload.generation.generation_ready)

    async def test_voice_layer_composer_respects_runtime_flags(self) -> None:
        composer = DefaultVoiceLayerComposer(
            knowledge_runtime_flags=KnowledgeRuntimeFlags(
                use_historical_context=False,
                use_editorial_knowledge=False,
                use_color_poetics=False,
            )
        )

        payload = await composer.compose(
            FashionReasoningOutput(
                response_type="text",
                text_response="Draft.",
                style_logic_points=["logic"],
                visual_language_points=["visual mood"],
                historical_note_candidates=["history note"],
                styling_rule_candidates=["rule"],
                editorial_context_candidates=["editorial note"],
                color_poetic_candidates=["ivory"],
                composition_theory_candidates=["diagonal composition"],
            ),
            VoiceContext(
                mode="style_exploration",
                response_type="text_with_visual_offer",
                desired_depth="deep",
                should_be_brief=False,
                can_use_historical_layer=True,
                can_use_color_poetics=True,
                can_offer_visual_cta=False,
                profile_context_present=False,
                knowledge_density="high",
            ),
        )

        self.assertEqual(payload.voice_layers_used, ["stylist", "color_poetics"])
        self.assertFalse(payload.includes_historical_note)
        self.assertTrue(payload.includes_color_poetics)
        self.assertEqual(payload.brevity_level, "deep")
        self.assertIn("Visually, visual mood.", payload.text)


if __name__ == "__main__":
    unittest.main()
