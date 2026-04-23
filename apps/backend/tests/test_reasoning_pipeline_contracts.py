from pathlib import Path
import unittest

from app.application.prompt_building.services.fashion_reasoning_service import (
    FashionReasoningInput as PromptFashionReasoningInput,
)
from app.application.reasoning import (
    DefaultFashionBriefBuilder,
    DefaultFashionReasoningContextAssembler,
    DefaultFashionReasoningPipeline,
    DefaultFashionReasoner,
    DefaultProfileStyleAlignmentService,
    DefaultReasoningOutputMapper,
    DefaultRetrievalProfileSelector,
    ProfileAlignedFashionReasoningContextAssembler,
    FashionBriefBuilder,
    FashionReasoner,
    FashionReasoningContextAssembler,
    FashionReasoningPipeline,
    ProfileStyleAlignmentService,
    ReasoningOutputMapper,
)
from app.domain.knowledge.entities import KnowledgeCard
from app.domain.knowledge.enums import KnowledgeType
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.reasoning import (
    FashionReasoningInput,
    FashionReasoningOutput,
    FashionReasoningPresentationPayload,
    GenerationHandoffPayload,
    ImageCtaCandidate,
    KnowledgeContext,
    ProfileAlignedStyleFacetBundle,
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
    StyleVisualLanguageFacet,
    UsedStyleReference,
    VoiceLayerReasoningPayload,
)
from app.domain.routing.entities.routing_decision import RoutingDecision
from app.domain.routing.enums.routing_mode import RoutingMode
from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints
from app.infrastructure.reasoning import StyleDistilledReasoningProvider


class ReasoningPipelineContractsTests(unittest.TestCase):
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
        self.assertEqual(input_contract.observability_counts()["style_image_facets_count"], 1)
        self.assertEqual(input_contract.observability_counts()["style_visual_cards"], 1)

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
        self.assertEqual(output.fashion_brief.hero_garments, ["translucent shell jacket"])
        self.assertEqual(output.fashion_brief.props, ["chrome headphones"])
        self.assertEqual(output.fashion_brief.photo_treatment, ["soft bloom"])
        self.assertEqual(output.fashion_brief.intent, "style_exploration")
        self.assertEqual(output.fashion_brief.style_direction, "Soft Futurism")
        self.assertEqual(output.reasoning_metadata, ReasoningMetadata())

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
                )
            ],
            relation_facets=[
                StyleRelationFacet(style_id=77, related_styles=["Romantic Academia"])
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
                palette=["espresso"],
                hero_garments=["wool blazer"],
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
        self.assertEqual(reasoning_input.style_facet_bundle().total_count(), 4)
        self.assertEqual(reasoning_input.style_history[0].style_name, "Dark Academia")
        self.assertEqual(reasoning_input.diversity_constraints.avoid_palette, ["espresso"])
        self.assertEqual(reasoning_input.style_semantic_fragments[0].fragment_type, "styling_rule")
        self.assertEqual(knowledge_provider.query.retrieval_profile, "visual_heavy")
        self.assertEqual(facet_provider.query.active_slots, {"occasion": "gallery"})

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
                        palette=["camel", "cream"],
                        hero_garments=["camel blazer"],
                    )
                ],
            ),
            profile_context=None,
            retrieval_profile=None,
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
        self.assertIn("image:42", reasoning_input.profile_facet_weights)


class DefaultFashionReasonerTests(unittest.IsolatedAsyncioTestCase):
    async def test_reasoner_returns_clarification_without_brief_when_required_slots_are_missing(self) -> None:
        reasoner = DefaultFashionReasoner()

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
                    )
                ],
                style_relation_facets=[
                    StyleRelationFacet(style_id=12, related_styles=["Y2K futurism"])
                ],
            )
        )

        self.assertEqual(output.response_type, "generation_ready")
        self.assertIn("soften technical garments with fluid layers", output.style_logic_points)
        self.assertIn("ice blue", output.visual_language_points)
        self.assertEqual(output.historical_note_candidates, ["Y2K futurism", "space-age minimalism"])
        self.assertTrue(output.can_offer_visualization)
        self.assertEqual(output.image_cta_candidates[0].required_generation_trigger, "generate_now")
        self.assertFalse(output.has_generation_handoff())


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
                    styling_rules=["balance translucent and matte textures"],
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
                )
            ],
            style_relation_facets=[
                StyleRelationFacet(style_id=12, related_styles=["Y2K futurism"])
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
        self.assertEqual(brief.secondary_garments, ["wide-leg silver trousers"])
        self.assertEqual(brief.garment_list, ["translucent shell jacket", "wide-leg silver trousers"])
        self.assertEqual(brief.palette, ["ice blue", "graphite"])
        self.assertEqual(brief.props, ["lucite clutch"])
        self.assertEqual(brief.photo_treatment, ["soft bloom"])
        self.assertEqual(brief.lighting_mood, ["diffused studio glow"])
        self.assertIn("avoid hard tactical cosplay", brief.negative_constraints)
        self.assertIn("image:12", brief.source_style_facet_ids)
        self.assertTrue(completed_output.has_generation_handoff())


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
        self.assertEqual(output.observability["routing_mode"], "style_exploration")
        self.assertEqual(output.observability["retrieval_profile"], "visual_heavy")
        self.assertEqual(output.observability["used_providers"], ["fake_style_provider"])
        self.assertTrue(output.observability["profile_alignment_applied"])
        self.assertGreaterEqual(output.observability["style_image_facets_count"], 1)
        self.assertTrue(output.observability["cta_offered"])
        self.assertEqual(output.reasoning_metadata.routing_mode, "style_exploration")
        self.assertEqual(output.reasoning_metadata.retrieval_profile, "visual_heavy")
        self.assertEqual(output.reasoning_metadata.used_providers, ["fake_style_provider"])
        self.assertTrue(output.reasoning_metadata.profile_alignment_applied)
        self.assertTrue(output.reasoning_metadata.fashion_brief_built)
        self.assertTrue(output.reasoning_metadata.generation_ready)

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
        self.assertFalse(output.observability["generation_ready"])

    async def test_pipeline_applies_anti_repeat_constraints_to_brief_and_observability(self) -> None:
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
        self.assertEqual(output.fashion_brief.hero_garments, ["structured cargo skirt"])
        self.assertEqual(output.fashion_brief.palette, ["ivory"])
        self.assertNotIn("wool blazer", output.fashion_brief.garment_list)
        self.assertNotIn("espresso", output.fashion_brief.palette)
        self.assertNotIn("espresso", output.fashion_brief.color_logic)
        self.assertIn("avoid recently used palette: espresso", output.fashion_brief.negative_constraints)
        self.assertIn("avoid recently used hero garment: wool blazer", output.fashion_brief.negative_constraints)
        self.assertEqual(output.fashion_brief.diversity_constraints["avoid_palette"], ["espresso"])
        self.assertEqual(output.observability["style_history_count"], 1)
        self.assertEqual(output.observability["diversity_constraints_present"], 1)


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
        payload = mapper.to_presentation(reasoning_output)

        self.assertIsInstance(payload, FashionReasoningPresentationPayload)
        self.assertIsInstance(payload.voice, VoiceLayerReasoningPayload)
        self.assertIsInstance(payload.generation, GenerationHandoffPayload)
        self.assertEqual(payload.voice.draft_text, reasoning_output.text_response)
        self.assertEqual(payload.voice.style_logic_points, reasoning_output.style_logic_points)
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
        payload = mapper.to_presentation(reasoning_output)

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

        payload = mapper.to_presentation(reasoning_output)

        self.assertEqual(payload.voice.response_type, "clarification")
        self.assertEqual(payload.voice.clarification_question, reasoning_output.clarification_question)
        self.assertFalse(payload.generation.generation_ready)
        self.assertIsNone(payload.generation.fashion_brief)
        self.assertEqual(payload.generation.blocked_reason, "clarification_required")


if __name__ == "__main__":
    unittest.main()
