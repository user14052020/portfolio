from app.application.reasoning.contracts import (
    FashionBriefBuilder,
    FashionReasoner,
    FashionReasoningContextAssembler,
)
from app.application.reasoning.services.fashion_brief_builder import DefaultFashionBriefBuilder
from app.application.reasoning.services.fashion_reasoner import DefaultFashionReasoner
from app.application.reasoning.services.profile_aligned_reasoning_context_assembler import (
    ProfileAlignedFashionReasoningContextAssembler,
)
from app.domain.reasoning import (
    FashionReasoningInput,
    FashionReasoningOutput,
    ProfileContextSnapshot,
    ReasoningMetadata,
    SessionStateSnapshot,
)
from app.domain.routing.entities.routing_decision import RoutingDecision


class DefaultFashionReasoningPipeline:
    def __init__(
        self,
        *,
        context_assembler: FashionReasoningContextAssembler | None = None,
        reasoner: FashionReasoner | None = None,
        brief_builder: FashionBriefBuilder | None = None,
    ) -> None:
        self._context_assembler = context_assembler or ProfileAlignedFashionReasoningContextAssembler()
        self._reasoner = reasoner or DefaultFashionReasoner()
        self._brief_builder = brief_builder or DefaultFashionBriefBuilder()

    async def run(
        self,
        *,
        routing_decision: RoutingDecision,
        session_state: SessionStateSnapshot,
        profile_context: ProfileContextSnapshot | None,
        retrieval_profile: str | None,
    ) -> FashionReasoningOutput:
        reasoning_input = await self._context_assembler.assemble(
            routing_decision=routing_decision,
            session_state=session_state,
            profile_context=profile_context,
            retrieval_profile=retrieval_profile,
        )
        reasoning_output = await self._reasoner.reason(reasoning_input)
        if reasoning_output.requires_clarification() or not reasoning_output.can_offer_visualization:
            observability = _pipeline_observability(
                reasoning_input=reasoning_input,
                reasoning_output=reasoning_output,
                fashion_brief_built=False,
                generation_ready=False,
            )
            return reasoning_output.model_copy(
                update={
                    "reasoning_metadata": ReasoningMetadata.from_observability(observability),
                    "observability": observability,
                },
                deep=True,
            )

        brief = await self._brief_builder.build(
            reasoning_input=reasoning_input,
            reasoning_output=reasoning_output,
        )
        generation_ready = reasoning_output.response_type == "generation_ready" and reasoning_input.can_generate_now
        observability = _pipeline_observability(
            reasoning_input=reasoning_input,
            reasoning_output=reasoning_output,
            fashion_brief_built=True,
            generation_ready=generation_ready,
        )
        return reasoning_output.model_copy(
            update={
                "fashion_brief": brief,
                "generation_ready": generation_ready,
                "reasoning_metadata": ReasoningMetadata.from_observability(observability),
                "observability": observability,
            },
            deep=True,
        )


def _pipeline_observability(
    *,
    reasoning_input: FashionReasoningInput,
    reasoning_output: FashionReasoningOutput,
    fashion_brief_built: bool,
    generation_ready: bool,
) -> dict[str, object]:
    return {
        **reasoning_output.observability,
        "routing_mode": reasoning_input.mode,
        "retrieval_profile": reasoning_input.retrieval_profile,
        "used_providers": list(reasoning_input.knowledge_context.providers_used),
        "profile_alignment_applied": reasoning_input.profile_alignment_applied,
        "profile_alignment_notes": list(reasoning_input.profile_alignment_notes),
        "profile_alignment_filtered_count": len(reasoning_input.profile_alignment_filtered_out),
        "clarification_required": reasoning_output.requires_clarification(),
        "fashion_brief_built": fashion_brief_built,
        "cta_offered": reasoning_output.can_offer_visualization,
        "generation_ready": generation_ready,
        **reasoning_input.observability_counts(),
    }
