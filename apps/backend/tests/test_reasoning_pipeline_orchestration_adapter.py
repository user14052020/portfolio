import unittest
from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionResult, DecisionType
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.application.stylist_chat.services.reasoning_pipeline_decision_adapter import (
    FashionReasoningPipelineDecisionAdapter,
)
from app.domain.chat_context import ChatModeContext, CommandContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.knowledge.entities import KnowledgeRuntimeFlags
from app.domain.reasoning import (
    FashionReasoningOutput,
    FashionReasoningPresentationPayload,
    GenerationHandoffPayload,
    ProfileContextSnapshot,
    ReasoningMetadata,
    SessionStateSnapshot,
    VoiceContext,
    VoiceRuntimeFlags,
    VoiceLayerReasoningPayload,
)
from app.domain.routing import RoutingDecision, RoutingMode


class FakeReasoningPipeline:
    def __init__(self, *, output: FashionReasoningOutput) -> None:
        self.output = output
        self.routing_decision: RoutingDecision | None = None
        self.session_state: SessionStateSnapshot | None = None
        self.profile_context: ProfileContextSnapshot | None = None
        self.retrieval_profile: str | None = None

    async def run(
        self,
        *,
        routing_decision: RoutingDecision,
        session_state: SessionStateSnapshot,
        profile_context,
        retrieval_profile: str | None,
    ) -> FashionReasoningOutput:
        self.routing_decision = routing_decision
        self.session_state = session_state
        self.profile_context = profile_context
        self.retrieval_profile = retrieval_profile
        return self.output


class FakeGenerationRequestBuilder:
    def __init__(self) -> None:
        self.structured_outfit_brief: dict[str, Any] | None = None
        self.reasoning_route: str | None = None
        self.profile_context_snapshot: ProfileContextSnapshot | None = None

    async def build_from_reasoning(self, **kwargs) -> DecisionResult:
        self.structured_outfit_brief = kwargs.get("structured_outfit_brief")
        self.reasoning_route = kwargs["reasoning_output"].route
        self.profile_context_snapshot = kwargs.get("profile_context_snapshot")
        return DecisionResult(
            decision_type=DecisionType.TEXT_ONLY,
            active_mode=kwargs["context"].active_mode,
            flow_state=FlowState.COMPLETED,
            text_reply=kwargs["reasoning_output"].reply_text,
        )

    def explicitly_requests_generation(self, text: str) -> bool:
        return "visualize" in text.lower()


class FailingPromptBuilder:
    async def build(self, *, brief: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("Prompt builder must not run before garment visualization confirmation")


class FakeReasoningOutputMapper:
    def __init__(self) -> None:
        self.reasoning_output: FashionReasoningOutput | None = None
        self.runtime_flags: KnowledgeRuntimeFlags | None = None
        self.voice_context: VoiceContext | None = None

    async def to_presentation(
        self,
        reasoning_output: FashionReasoningOutput,
        *,
        voice_context=None,
        runtime_flags: KnowledgeRuntimeFlags | None = None,
    ) -> FashionReasoningPresentationPayload:
        self.reasoning_output = reasoning_output
        self.runtime_flags = runtime_flags
        self.voice_context = voice_context
        return FashionReasoningPresentationPayload(
            voice=VoiceLayerReasoningPayload(
                response_type=reasoning_output.response_type,
                draft_text="Voice-shaped response from presentation payload.",
                tone_profile="smart_stylist_balanced",
                voice_layers_used=["stylist"],
                includes_historical_note=False,
                includes_color_poetics=False,
                cta_text="If it helps, I can show this as a flat lay reference.",
                brevity_level="normal",
                style_logic_points=["keep the silhouette clean"],
                visual_language_points=["soft contrast"],
                can_offer_visualization=reasoning_output.can_offer_visualization,
                suggested_cta=reasoning_output.suggested_cta,
                observability={
                    "voice_cta_style": "soft",
                },
            ),
            generation=GenerationHandoffPayload(
                generation_ready=False,
                fashion_brief=None,
                blocked_reason="generation_not_ready",
            ),
            observability={"mapper_used": True},
        )


class FakeKnowledgeRuntimeSettingsProvider:
    def __init__(self, runtime_flags: KnowledgeRuntimeFlags) -> None:
        self.runtime_flags = runtime_flags

    async def get_runtime_flags(self) -> KnowledgeRuntimeFlags:
        return self.runtime_flags

    async def get_provider_priorities(self) -> dict[str, int]:
        return {}


class FakeVoiceRuntimeSettingsProvider:
    def __init__(self, runtime_flags: VoiceRuntimeFlags) -> None:
        self.runtime_flags = runtime_flags

    async def get_runtime_flags(self) -> VoiceRuntimeFlags:
        return self.runtime_flags


class ReasoningPipelineOrchestrationAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_adapter_uses_routing_snapshot_and_passes_fashion_brief_to_generation_handoff(self) -> None:
        brief = FashionBrief(
            intent="general_advice",
            style_direction="Soft Futurism",
            hero_garments=["translucent jacket"],
            garment_list=["translucent jacket", "silver trousers"],
            palette=["ice blue", "graphite"],
            composition_rules=["asymmetric flatlay"],
            tailoring_logic=["soft technical layering"],
            color_logic=["cool pearlescent contrast"],
        )
        output = FashionReasoningOutput(
            response_type="visual_offer",
            text_response="Use soft technical layering with cool contrast.",
            can_offer_visualization=True,
            suggested_cta="Build a flat lay reference?",
            fashion_brief=brief,
            reasoning_metadata=ReasoningMetadata(
                retrieval_profile="style_focused",
                style_facets_count=4,
                fashion_brief_built=True,
                cta_offered=True,
            ),
            observability={"retrieval_profile": "style_focused"},
        )
        pipeline = FakeReasoningPipeline(output=output)
        generation_builder = FakeGenerationRequestBuilder()
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=pipeline,
            generation_request_builder=generation_builder,
        )
        context = ChatModeContext(
            active_mode=ChatMode.GENERAL_ADVICE,
            command_context=CommandContext(
                metadata={
                    "routing_decision": RoutingDecision(
                        mode=RoutingMode.GENERAL_ADVICE,
                        retrieval_profile="style_focused",
                    ).model_dump(mode="json")
                }
            ),
        )

        decision = await adapter.handle(
            command=ChatCommand(
                session_id="adapter-1",
                locale="en",
                message="Modernize a white shirt",
                profile_context={"preferred_colors": "ice blue"},
            ),
            context=context,
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
        )

        self.assertEqual(pipeline.retrieval_profile, "style_focused")
        self.assertEqual(pipeline.session_state.user_request, "Modernize a white shirt")
        self.assertIsNotNone(pipeline.profile_context)
        assert pipeline.profile_context is not None
        self.assertEqual(pipeline.profile_context.source, "profile_context_service")
        self.assertEqual(pipeline.profile_context.color_preferences, ("ice blue",))
        self.assertEqual(generation_builder.reasoning_route, "text_and_generation")
        self.assertIsNotNone(generation_builder.profile_context_snapshot)
        assert generation_builder.profile_context_snapshot is not None
        self.assertEqual(
            generation_builder.profile_context_snapshot.color_preferences,
            ("ice blue",),
        )
        self.assertEqual(generation_builder.structured_outfit_brief["style_identity"], "Soft Futurism")
        self.assertEqual(decision.decision_type, DecisionType.TEXT_ONLY)
        self.assertTrue(decision.can_offer_visualization)
        self.assertEqual(decision.flow_state, FlowState.READY_FOR_GENERATION)
        self.assertTrue(decision.telemetry["reasoning_pipeline_used"])
        self.assertEqual(decision.telemetry["reasoning_response_type"], "visual_offer")
        self.assertEqual(decision.telemetry["reasoning_retrieval_profile"], "style_focused")
        self.assertEqual(decision.telemetry["reasoning_style_facets_count"], 4)
        self.assertTrue(decision.telemetry["reasoning_profile_context_present"])
        self.assertEqual(decision.telemetry["reasoning_profile_context_source"], "profile_context_service")
        self.assertEqual(decision.telemetry["reasoning_profile_fields_count"], 1)
        self.assertEqual(decision.telemetry["reasoning_profile_derived_constraints_count"], 0)
        self.assertTrue(decision.telemetry["reasoning_brief_built"])
        self.assertTrue(decision.telemetry["reasoning_cta_offered"])
        self.assertFalse(decision.telemetry["reasoning_generation_ready"])
        self.assertFalse(decision.telemetry["reasoning_clarification_required"])

    async def test_adapter_uses_voice_ready_presentation_payload_for_reply_text(self) -> None:
        output = FashionReasoningOutput(
            response_type="text",
            text_response="Raw reasoning draft should not be returned directly.",
            style_logic_points=["raw logic"],
            visual_language_points=["raw visual"],
            can_offer_visualization=False,
            reasoning_metadata=ReasoningMetadata(retrieval_profile="light"),
            observability={
                "retrieval_profile": "light",
                "cta_decision_reason": "clarification_required",
                "cta_confidence_score": 0.35,
                "profile_signals_sufficient": False,
                "reasoning_is_mostly_advisory": True,
                "profile_completeness_state": "missing",
                "profile_clarification_decision": "not_profile_related",
                "profile_alignment_boosted_categories": ["advice"],
                "profile_alignment_removed_item_types": ["palette"],
                "style_logic_points_count": 1,
                "visual_language_points_count": 1,
                "historical_note_candidates_count": 0,
                "styling_rule_candidates_count": 0,
                "anti_repeat_hero_garments_avoided_count": 1,
                "anti_repeat_accessories_avoided_count": 0,
                "anti_repeat_composition_cues_avoided_count": 2,
                "anti_repeat_visual_motifs_avoided_count": 1,
            },
        )
        pipeline = FakeReasoningPipeline(output=output)
        mapper = FakeReasoningOutputMapper()
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=pipeline,
            reasoning_output_mapper=mapper,
            generation_request_builder=FakeGenerationRequestBuilder(),
        )

        decision = await adapter.handle(
            command=ChatCommand(
                session_id="adapter-voice-payload-1",
                locale="en",
                message="How should this outfit feel?",
            ),
            context=ChatModeContext(active_mode=ChatMode.GENERAL_ADVICE),
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
        )

        self.assertIs(mapper.reasoning_output, output)
        self.assertIsNotNone(mapper.voice_context)
        assert mapper.voice_context is not None
        self.assertEqual(mapper.voice_context.mode, "general_advice")
        self.assertEqual(mapper.voice_context.response_type, "text_only")
        self.assertEqual(mapper.voice_context.desired_depth, "light")
        self.assertEqual(mapper.voice_context.locale, "en")
        self.assertEqual(decision.text_reply, "Voice-shaped response from presentation payload.")
        self.assertTrue(decision.telemetry["reasoning_voice_payload_ready"])
        self.assertFalse(decision.telemetry["reasoning_generation_handoff_ready"])
        self.assertEqual(decision.telemetry["reasoning_generation_blocked_reason"], "generation_not_ready")
        self.assertEqual(decision.telemetry["reasoning_voice_style_logic_points_count"], 1)
        self.assertEqual(decision.telemetry["reasoning_voice_visual_language_points_count"], 1)
        self.assertEqual(decision.telemetry["reasoning_voice_mode"], "general_advice")
        self.assertEqual(decision.telemetry["reasoning_voice_response_type"], "text_only")
        self.assertEqual(decision.telemetry["reasoning_voice_desired_depth"], "light")
        self.assertEqual(decision.telemetry["reasoning_voice_knowledge_density"], "low")
        self.assertTrue(decision.telemetry["reasoning_voice_should_be_brief"])
        self.assertFalse(decision.telemetry["reasoning_voice_profile_context_present"])
        self.assertEqual(decision.telemetry["reasoning_voice_tone_profile"], "smart_stylist_balanced")
        self.assertEqual(decision.telemetry["reasoning_voice_layers_used"], ["stylist"])
        self.assertFalse(decision.telemetry["reasoning_voice_historical_used"])
        self.assertFalse(decision.telemetry["reasoning_voice_color_poetics_used"])
        self.assertEqual(decision.telemetry["reasoning_voice_brevity_level"], "normal")
        self.assertTrue(decision.telemetry["reasoning_voice_cta_present"])
        self.assertEqual(decision.telemetry["reasoning_voice_cta_style"], "soft")
        self.assertEqual(
            decision.telemetry["reasoning_voice_text_length"],
            len("Voice-shaped response from presentation payload."),
        )
        self.assertFalse(decision.telemetry["reasoning_profile_context_present"])
        self.assertIsNone(decision.telemetry["reasoning_profile_context_source"])
        self.assertEqual(decision.telemetry["reasoning_profile_fields_count"], 0)
        self.assertEqual(decision.telemetry["reasoning_profile_derived_constraints_count"], 0)
        self.assertEqual(decision.telemetry["reasoning_profile_completeness_state"], "missing")
        self.assertEqual(decision.telemetry["reasoning_profile_clarification_decision"], "not_profile_related")
        self.assertEqual(decision.telemetry["reasoning_profile_alignment_boosted_categories"], ["advice"])
        self.assertEqual(decision.telemetry["reasoning_profile_alignment_removed_item_types"], ["palette"])
        self.assertEqual(decision.telemetry["cta_decision_reason"], "clarification_required")
        self.assertEqual(decision.telemetry["cta_confidence_score"], 0.35)
        self.assertFalse(decision.telemetry["profile_signals_sufficient"])
        self.assertTrue(decision.telemetry["reasoning_is_mostly_advisory"])
        self.assertEqual(decision.telemetry["style_logic_points_count"], 1)
        self.assertEqual(decision.telemetry["visual_language_points_count"], 1)
        self.assertEqual(decision.telemetry["anti_repeat_hero_garments_avoided_count"], 1)
        self.assertEqual(decision.telemetry["anti_repeat_composition_cues_avoided_count"], 2)

    async def test_adapter_passes_runtime_flags_to_reasoning_output_mapper(self) -> None:
        output = FashionReasoningOutput(
            response_type="text",
            text_response="Runtime-aware draft.",
            historical_note_candidates=["history note"],
            editorial_context_candidates=["editorial note"],
            color_poetic_candidates=["ivory"],
            composition_theory_candidates=["diagonal composition"],
            can_offer_visualization=False,
        )
        mapper = FakeReasoningOutputMapper()
        runtime_flags = KnowledgeRuntimeFlags(
            use_historical_context=False,
            use_editorial_knowledge=False,
            use_color_poetics=False,
        )
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=FakeReasoningPipeline(output=output),
            reasoning_output_mapper=mapper,
            generation_request_builder=FakeGenerationRequestBuilder(),
            knowledge_runtime_settings_provider=FakeKnowledgeRuntimeSettingsProvider(runtime_flags),
        )

        await adapter.handle(
            command=ChatCommand(
                session_id="adapter-runtime-flags-1",
                locale="en",
                message="Keep this text-first.",
            ),
            context=ChatModeContext(active_mode=ChatMode.GENERAL_ADVICE),
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
        )

        self.assertIsNotNone(mapper.runtime_flags)
        assert mapper.runtime_flags is not None
        self.assertFalse(mapper.runtime_flags.use_historical_context)
        self.assertFalse(mapper.runtime_flags.use_editorial_knowledge)
        self.assertFalse(mapper.runtime_flags.use_color_poetics)

    async def test_adapter_passes_explicit_voice_context_and_voice_cta_to_visual_offer(self) -> None:
        output = FashionReasoningOutput(
            response_type="visual_offer",
            text_response="Let's keep the line long and quiet.",
            historical_note_candidates=["late modernist restraint"],
            color_poetic_candidates=["quiet pearl light"],
            can_offer_visualization=True,
            suggested_cta="Show this as a flat lay reference.",
            reasoning_metadata=ReasoningMetadata(retrieval_profile="style_focused", cta_offered=True),
            observability={"retrieval_profile": "style_focused"},
        )
        mapper = FakeReasoningOutputMapper()
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=FakeReasoningPipeline(output=output),
            reasoning_output_mapper=mapper,
            generation_request_builder=FakeGenerationRequestBuilder(),
        )

        decision = await adapter.handle(
            command=ChatCommand(
                session_id="adapter-voice-context-1",
                locale="en",
                message="Show another style direction",
                profile_context={"preferred_colors": "ivory"},
            ),
            context=ChatModeContext(active_mode=ChatMode.STYLE_EXPLORATION),
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
        )

        assert mapper.voice_context is not None
        self.assertEqual(mapper.voice_context.mode, "style_exploration")
        self.assertEqual(mapper.voice_context.response_type, "text_with_visual_offer")
        self.assertEqual(mapper.voice_context.desired_depth, "deep")
        self.assertEqual(mapper.voice_context.knowledge_density, "low")
        self.assertEqual(mapper.voice_context.locale, "en")
        self.assertTrue(mapper.voice_context.can_offer_visual_cta)
        self.assertTrue(mapper.voice_context.profile_context_present)
        self.assertEqual(decision.telemetry["reasoning_voice_mode"], "style_exploration")
        self.assertEqual(decision.telemetry["reasoning_voice_response_type"], "text_with_visual_offer")
        self.assertEqual(decision.telemetry["reasoning_voice_desired_depth"], "deep")
        self.assertEqual(decision.telemetry["reasoning_voice_knowledge_density"], "low")
        self.assertFalse(decision.telemetry["reasoning_voice_should_be_brief"])
        self.assertTrue(decision.telemetry["reasoning_voice_profile_context_present"])
        self.assertEqual(decision.telemetry["reasoning_voice_cta_style"], "soft")
        self.assertTrue(decision.can_offer_visualization)
        assert decision.visualization_offer is not None
        self.assertEqual(
            decision.visualization_offer.cta_text,
            "If it helps, I can show this as a flat lay reference.",
        )

    async def test_adapter_default_mapper_uses_live_voice_runtime_settings_provider(self) -> None:
        output = FashionReasoningOutput(
            response_type="visual_offer",
            text_response="Keep the silhouette long and quiet.",
            historical_note_candidates=["late modernist restraint"],
            color_poetic_candidates=["quiet pearl light"],
            can_offer_visualization=True,
            suggested_cta="I can show this as a flat lay reference.",
        )
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=FakeReasoningPipeline(output=output),
            generation_request_builder=FakeGenerationRequestBuilder(),
            voice_runtime_settings_provider=FakeVoiceRuntimeSettingsProvider(
                VoiceRuntimeFlags(
                    historian_enabled=False,
                    color_poetics_enabled=False,
                    deep_mode_enabled=False,
                    cta_experimental_copy_enabled=False,
                )
            ),
        )

        decision = await adapter.handle(
            command=ChatCommand(
                session_id="adapter-live-voice-flags-1",
                locale="en",
                message="Show another style direction",
            ),
            context=ChatModeContext(active_mode=ChatMode.STYLE_EXPLORATION),
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
        )

        assert decision.text_reply is not None
        self.assertNotIn("Historically,", decision.text_reply)
        self.assertNotIn("Visually,", decision.text_reply)
        self.assertTrue(decision.can_offer_visualization)
        self.assertEqual(
            decision.cta_text,
            "If you want, I can show this as a flat lay reference.",
        )

    async def test_adapter_merges_session_and_recent_profile_sources_through_profile_context_service(self) -> None:
        output = FashionReasoningOutput(
            response_type="text",
            text_response="Profile-aware reply.",
            can_offer_visualization=False,
            reasoning_metadata=ReasoningMetadata(retrieval_profile="light"),
            observability={"retrieval_profile": "light"},
        )
        pipeline = FakeReasoningPipeline(output=output)
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=pipeline,
            generation_request_builder=FakeGenerationRequestBuilder(),
        )

        await adapter.handle(
            command=ChatCommand(
                session_id="adapter-profile-merge-1",
                locale="en",
                message="Build me a cleaner outfit direction",
                profile_context={"fit": "relaxed"},
                metadata={
                    "session_profile_context": {
                        "preferred_items": ["long coat"],
                        "presentation_profile": "androgynous",
                        "height_cm": 176,
                    },
                    "profile_recent_updates": {
                        "avoid_items": ["heels"],
                        "weight_kg": 63,
                    },
                },
            ),
            context=ChatModeContext(active_mode=ChatMode.GENERAL_ADVICE),
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
        )

        assert pipeline.profile_context is not None
        self.assertEqual(pipeline.profile_context.presentation_profile, "androgynous")
        self.assertEqual(pipeline.profile_context.fit_preferences, ("relaxed",))
        self.assertEqual(pipeline.profile_context.preferred_items, ("long coat",))
        self.assertEqual(pipeline.profile_context.avoided_items, ("heels",))
        self.assertEqual(pipeline.profile_context.values["height_cm"], 176)
        self.assertEqual(pipeline.profile_context.values["weight_kg"], 63)
        self.assertTrue(pipeline.profile_context.present)

    async def test_adapter_carries_explicit_anti_repeat_constraints_into_reasoning_snapshot(self) -> None:
        output = FashionReasoningOutput(
            response_type="text",
            text_response="Keep this direction text-first.",
            can_offer_visualization=False,
            reasoning_metadata=ReasoningMetadata(retrieval_profile="light"),
            observability={"retrieval_profile": "light"},
        )
        pipeline = FakeReasoningPipeline(output=output)
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=pipeline,
            generation_request_builder=FakeGenerationRequestBuilder(),
        )

        await adapter.handle(
            command=ChatCommand(
                session_id="adapter-constraints-1",
                locale="en",
                message="Try another style without repeating the last one",
            ),
            context=ChatModeContext(active_mode=ChatMode.STYLE_EXPLORATION),
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints={
                "avoid_palette": ["espresso"],
                "avoid_hero_garments": ["wool blazer"],
                "target_visual_distance": "high",
            },
        )

        assert pipeline.session_state is not None
        assert pipeline.session_state.diversity_constraints is not None
        self.assertEqual(pipeline.session_state.diversity_constraints.avoid_palette, ["espresso"])
        self.assertEqual(pipeline.session_state.diversity_constraints.avoid_hero_garments, ["wool blazer"])
        self.assertEqual(pipeline.session_state.diversity_constraints.target_visual_distance, "high")

    async def test_adapter_merges_structured_outfit_brief_with_reasoning_fashion_brief(self) -> None:
        brief = FashionBrief(
            intent="garment_matching",
            style_direction="Gallery Utility",
            style_identity="Gallery Utility",
            brief_mode="garment_matching",
            hero_garments=["black leather jacket"],
            garment_list=["black leather jacket", "straight wool trousers"],
            palette=["black", "warm grey"],
            color_logic=["Keep black as the visual anchor."],
            negative_constraints=["avoid loud competing jackets"],
        )
        output = FashionReasoningOutput(
            response_type="generation_ready",
            text_response="Build around the jacket with a cleaner gallery-ready base.",
            can_offer_visualization=True,
            fashion_brief=brief,
            generation_ready=True,
            reasoning_metadata=ReasoningMetadata(
                retrieval_profile="visual_heavy",
                fashion_brief_built=True,
                generation_ready=True,
            ),
            observability={"retrieval_profile": "visual_heavy", "generation_ready": True},
        )
        pipeline = FakeReasoningPipeline(output=output)
        generation_builder = FakeGenerationRequestBuilder()
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=pipeline,
            generation_request_builder=generation_builder,
        )

        await adapter.handle(
            command=ChatCommand(
                session_id="adapter-brief-merge-1",
                locale="en",
                message="Build around my black leather jacket",
            ),
            context=ChatModeContext(active_mode=ChatMode.GARMENT_MATCHING),
            must_generate=True,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
            structured_outfit_brief={
                "brief_type": "garment_matching",
                "anchor_summary": "black leather jacket",
                "anchor_garment": {"garment_type": "jacket", "material": "leather", "color_primary": "black"},
                "color_logic": ["Echo the anchor tone in footwear."],
            },
        )

        assert pipeline.session_state is not None
        self.assertEqual(pipeline.session_state.active_slots["brief_type"], "garment_matching")
        self.assertEqual(pipeline.session_state.active_slots["anchor_summary"], "black leather jacket")
        self.assertEqual(pipeline.session_state.active_slots["anchor_garment"], "jacket")
        self.assertEqual(pipeline.session_state.active_slots["anchor_material"], "leather")
        self.assertEqual(pipeline.session_state.active_slots["anchor_color"], "black")
        assert generation_builder.structured_outfit_brief is not None
        self.assertEqual(generation_builder.structured_outfit_brief["brief_type"], "garment_matching")
        self.assertEqual(generation_builder.structured_outfit_brief["anchor_summary"], "black leather jacket")
        self.assertEqual(
            generation_builder.structured_outfit_brief["anchor_garment"]["garment_type"],
            "jacket",
        )
        self.assertEqual(generation_builder.structured_outfit_brief["style_identity"], "Gallery Utility")
        self.assertEqual(
            generation_builder.structured_outfit_brief["reasoning_fashion_brief"]["style_identity"],
            "Gallery Utility",
        )
        self.assertEqual(
            generation_builder.structured_outfit_brief["color_logic"],
            ["Echo the anchor tone in footwear.", "Keep black as the visual anchor."],
        )

    async def test_adapter_keeps_garment_matching_text_first_until_visual_confirmation(self) -> None:
        brief = FashionBrief(
            intent="garment_matching",
            style_direction="Gallery Utility",
            style_identity="Gallery Utility",
            brief_mode="garment_matching",
            hero_garments=["black leather jacket"],
            garment_list=["black leather jacket", "straight wool trousers"],
            palette=["black", "warm grey"],
            composition_rules=["center the anchor garment"],
        )
        output = FashionReasoningOutput(
            response_type="visual_offer",
            text_response="Build around the jacket with a cleaner gallery-ready base.",
            can_offer_visualization=True,
            suggested_cta="Visualize this direction",
            fashion_brief=brief,
            reasoning_metadata=ReasoningMetadata(
                retrieval_profile="visual_heavy",
                fashion_brief_built=True,
                cta_offered=True,
            ),
            observability={"retrieval_profile": "visual_heavy"},
        )
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=FakeReasoningPipeline(output=output),
            generation_request_builder=GenerationRequestBuilder(prompt_builder=FailingPromptBuilder()),
        )

        decision = await adapter.handle(
            command=ChatCommand(
                session_id="adapter-garment-text-first-1",
                locale="en",
                message="Build around my black leather jacket",
            ),
            context=ChatModeContext(active_mode=ChatMode.GARMENT_MATCHING),
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
            structured_outfit_brief={
                "brief_type": "garment_matching",
                "anchor_summary": "black leather jacket",
                "anchor_garment": {"garment_type": "jacket", "material": "leather", "color_primary": "black"},
            },
        )

        self.assertEqual(decision.decision_type, DecisionType.TEXT_ONLY)
        self.assertIsNone(decision.generation_payload)
        self.assertTrue(decision.can_offer_visualization)
        self.assertEqual(decision.cta_text, "Build a flat lay around this garment?")
        self.assertEqual(decision.flow_state, FlowState.READY_FOR_GENERATION)
        self.assertTrue(decision.telemetry["reasoning_pipeline_used"])

    async def test_adapter_extracts_occasion_brief_slots_into_reasoning_snapshot(self) -> None:
        output = FashionReasoningOutput(
            response_type="text",
            text_response="Keep the occasion advice text-first.",
            can_offer_visualization=False,
            reasoning_metadata=ReasoningMetadata(retrieval_profile="occasion_focused"),
            observability={"retrieval_profile": "occasion_focused"},
        )
        pipeline = FakeReasoningPipeline(output=output)
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=pipeline,
            generation_request_builder=FakeGenerationRequestBuilder(),
        )

        await adapter.handle(
            command=ChatCommand(
                session_id="adapter-occasion-slots-1",
                locale="en",
                message="What should I wear to the exhibition?",
            ),
            context=ChatModeContext(active_mode=ChatMode.OCCASION_OUTFIT),
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
            structured_outfit_brief={
                "brief_type": "occasion_outfit",
                "styling_goal": "Build an event-aware outfit.",
                "occasion_context": {
                    "event_type": "exhibition",
                    "dress_code": "smart casual",
                    "location": "gallery",
                    "time_of_day": "evening",
                    "desired_impression": "polished",
                    "season": "spring",
                },
            },
        )

        assert pipeline.session_state is not None
        self.assertEqual(pipeline.session_state.active_slots["brief_type"], "occasion_outfit")
        self.assertEqual(pipeline.session_state.active_slots["occasion"], "exhibition")
        self.assertEqual(pipeline.session_state.active_slots["dress_code"], "smart casual")
        self.assertEqual(pipeline.session_state.active_slots["location"], "gallery")
        self.assertEqual(pipeline.session_state.active_slots["time_of_day"], "evening")
        self.assertEqual(pipeline.session_state.active_slots["desired_impression"], "polished")
        self.assertEqual(pipeline.session_state.active_slots["weather"], "spring")

    async def test_adapter_keeps_occasion_outfit_text_first_until_visual_confirmation(self) -> None:
        brief = FashionBrief(
            intent="occasion_outfit",
            style_direction="Gallery Evening",
            style_identity="Gallery Evening",
            brief_mode="occasion_outfit",
            hero_garments=["tailored ivory blazer"],
            garment_list=["tailored ivory blazer", "fluid black trousers"],
            palette=["ivory", "black", "soft metallic"],
            composition_rules=["event-aware polished flat lay"],
        )
        output = FashionReasoningOutput(
            response_type="visual_offer",
            text_response="Keep the exhibition outfit polished, mobile, and quietly expressive.",
            can_offer_visualization=True,
            suggested_cta="Visualize this occasion look",
            fashion_brief=brief,
            reasoning_metadata=ReasoningMetadata(
                retrieval_profile="occasion_focused",
                fashion_brief_built=True,
                cta_offered=True,
            ),
            observability={"retrieval_profile": "occasion_focused"},
        )
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=FakeReasoningPipeline(output=output),
            generation_request_builder=GenerationRequestBuilder(prompt_builder=FailingPromptBuilder()),
        )

        decision = await adapter.handle(
            command=ChatCommand(
                session_id="adapter-occasion-text-first-1",
                locale="en",
                message="Spring evening exhibition, polished",
            ),
            context=ChatModeContext(active_mode=ChatMode.OCCASION_OUTFIT),
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
            structured_outfit_brief={
                "brief_type": "occasion_outfit",
                "styling_goal": "Build an event-aware outfit.",
                "occasion_context": {
                    "event_type": "exhibition",
                    "dress_code": "smart casual",
                    "time_of_day": "evening",
                    "desired_impression": "polished",
                    "season": "spring",
                },
            },
        )

        self.assertEqual(decision.decision_type, DecisionType.TEXT_ONLY)
        self.assertIsNone(decision.generation_payload)
        self.assertTrue(decision.can_offer_visualization)
        self.assertEqual(decision.cta_text, "Build a flat lay for this occasion?")
        self.assertEqual(decision.flow_state, FlowState.READY_FOR_GENERATION)
        self.assertTrue(decision.telemetry["reasoning_pipeline_used"])

    async def test_adapter_preserves_style_exploration_context_for_generation_handoff(self) -> None:
        brief = FashionBrief(
            intent="style_exploration",
            style_direction="Neo Romantic Utility",
            style_identity="Neo Romantic Utility",
            brief_mode="style_exploration",
            hero_garments=["structured cargo skirt"],
            garment_list=["structured cargo skirt", "ivory knit shell"],
            palette=["ivory", "graphite"],
            composition_rules=["editorial flat lay with negative space"],
            diversity_constraints={"target_visual_distance": "high"},
        )
        output = FashionReasoningOutput(
            response_type="generation_ready",
            text_response="Use an adjacent style direction with a cleaner silhouette.",
            can_offer_visualization=True,
            suggested_cta="Visualize this direction",
            fashion_brief=brief,
            generation_ready=True,
            reasoning_metadata=ReasoningMetadata(
                retrieval_profile="visual_heavy",
                style_facets_count=4,
                fashion_brief_built=True,
                cta_offered=True,
                generation_ready=True,
            ),
            observability={"retrieval_profile": "visual_heavy", "generation_ready": True},
        )
        pipeline = FakeReasoningPipeline(output=output)
        generation_builder = FakeGenerationRequestBuilder()
        adapter = FashionReasoningPipelineDecisionAdapter(
            reasoning_pipeline=pipeline,
            generation_request_builder=generation_builder,
        )
        context = ChatModeContext(
            active_mode=ChatMode.STYLE_EXPLORATION,
            current_style_id="neo-romantic-utility",
            current_style_name="Neo Romantic Utility",
            style_history=[
                {
                    "style_id": "artful-minimalism",
                    "style_name": "Artful Minimalism",
                    "style_family": "modern minimalism",
                    "silhouette_family": "clean and elongated",
                    "palette": ["espresso", "stone"],
                    "hero_garments": ["wool blazer"],
                    "styling_mood": ["quiet tailoring"],
                }
            ],
            command_context=CommandContext(
                metadata={
                    "routing_decision": RoutingDecision(
                        mode=RoutingMode.STYLE_EXPLORATION,
                        generation_intent=True,
                        retrieval_profile="visual_heavy",
                        requires_style_retrieval=True,
                    ).model_dump(mode="json")
                }
            ),
        )

        decision = await adapter.handle(
            command=ChatCommand(
                session_id="adapter-style-1",
                locale="en",
                message="Try another style",
                command_name="style_exploration",
                command_step="start",
                metadata={"source": "quick_action"},
            ),
            context=context,
            must_generate=True,
            style_seed={"slug": "neo-romantic-utility", "title": "Neo Romantic Utility"},
            previous_style_directions=[
                {"style_id": "old-style", "style_name": "Soft Academia"},
            ],
            occasion_context=None,
            anti_repeat_constraints={
                "avoid_palette": ["espresso"],
                "avoid_hero_garments": ["wool blazer"],
                "target_visual_distance": "high",
            },
            structured_outfit_brief={"intent": "style_exploration"},
        )

        assert pipeline.routing_decision is not None
        assert pipeline.session_state is not None
        assert pipeline.session_state.diversity_constraints is not None
        self.assertEqual(pipeline.routing_decision.mode, RoutingMode.STYLE_EXPLORATION)
        self.assertEqual(pipeline.retrieval_profile, "visual_heavy")
        self.assertEqual(pipeline.session_state.current_style_id, "neo-romantic-utility")
        self.assertEqual(pipeline.session_state.current_style_name, "Neo Romantic Utility")
        self.assertEqual(
            pipeline.session_state.style_history[0].silhouette_family,
            "clean and elongated",
        )
        self.assertEqual(pipeline.session_state.diversity_constraints.avoid_palette, ["espresso"])
        self.assertEqual(pipeline.session_state.diversity_constraints.avoid_hero_garments, ["wool blazer"])
        self.assertEqual(pipeline.session_state.diversity_constraints.target_visual_distance, "high")
        self.assertEqual(generation_builder.reasoning_route, "text_and_generation")
        self.assertEqual(generation_builder.structured_outfit_brief["style_identity"], "Neo Romantic Utility")
        self.assertEqual(decision.flow_state, FlowState.READY_FOR_GENERATION)
        self.assertTrue(decision.telemetry["reasoning_pipeline_used"])
        self.assertTrue(decision.telemetry["reasoning_generation_ready"])


if __name__ == "__main__":
    unittest.main()
