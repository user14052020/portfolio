import unittest
from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionResult, DecisionType
from app.application.stylist_chat.services.reasoning_pipeline_decision_adapter import (
    FashionReasoningPipelineDecisionAdapter,
)
from app.domain.chat_context import ChatModeContext, CommandContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.reasoning import (
    FashionReasoningOutput,
    ReasoningMetadata,
    SessionStateSnapshot,
)
from app.domain.routing import RoutingDecision, RoutingMode


class FakeReasoningPipeline:
    def __init__(self, *, output: FashionReasoningOutput) -> None:
        self.output = output
        self.routing_decision: RoutingDecision | None = None
        self.session_state: SessionStateSnapshot | None = None
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
        self.retrieval_profile = retrieval_profile
        return self.output


class FakeGenerationRequestBuilder:
    def __init__(self) -> None:
        self.structured_outfit_brief: dict[str, Any] | None = None
        self.reasoning_route: str | None = None

    async def build_from_reasoning(self, **kwargs) -> DecisionResult:
        self.structured_outfit_brief = kwargs.get("structured_outfit_brief")
        self.reasoning_route = kwargs["reasoning_output"].route
        return DecisionResult(
            decision_type=DecisionType.TEXT_ONLY,
            active_mode=kwargs["context"].active_mode,
            flow_state=FlowState.COMPLETED,
            text_reply=kwargs["reasoning_output"].reply_text,
        )

    def explicitly_requests_generation(self, text: str) -> bool:
        return "visualize" in text.lower()


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
        self.assertEqual(generation_builder.reasoning_route, "text_and_generation")
        self.assertEqual(generation_builder.structured_outfit_brief["style_identity"], "Soft Futurism")
        self.assertEqual(decision.decision_type, DecisionType.TEXT_ONLY)
        self.assertTrue(decision.can_offer_visualization)
        self.assertEqual(decision.flow_state, FlowState.READY_FOR_GENERATION)
        self.assertTrue(decision.telemetry["reasoning_pipeline_used"])


if __name__ == "__main__":
    unittest.main()
