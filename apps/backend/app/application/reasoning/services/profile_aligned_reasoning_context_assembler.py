from app.application.reasoning.contracts import (
    FashionReasoningContextAssembler,
    ProfileStyleAlignmentService,
)
from app.application.reasoning.services.fashion_reasoning_context_assembler import (
    DefaultFashionReasoningContextAssembler,
)
from app.application.reasoning.services.profile_style_alignment_service import (
    DefaultProfileStyleAlignmentService,
)
from app.domain.reasoning import (
    FashionReasoningInput,
    ProfileContextSnapshot,
    SessionStateSnapshot,
)
from app.domain.routing.entities.routing_decision import RoutingDecision


class ProfileAlignedFashionReasoningContextAssembler:
    def __init__(
        self,
        *,
        context_assembler: FashionReasoningContextAssembler | None = None,
        alignment_service: ProfileStyleAlignmentService | None = None,
    ) -> None:
        self._context_assembler = context_assembler or DefaultFashionReasoningContextAssembler()
        self._alignment_service = alignment_service or DefaultProfileStyleAlignmentService()

    async def assemble(
        self,
        *,
        routing_decision: RoutingDecision,
        session_state: SessionStateSnapshot,
        profile_context: ProfileContextSnapshot | None,
        retrieval_profile: str | None,
    ) -> FashionReasoningInput:
        reasoning_input = await self._context_assembler.assemble(
            routing_decision=routing_decision,
            session_state=session_state,
            profile_context=profile_context,
            retrieval_profile=retrieval_profile,
        )
        if profile_context is None:
            return reasoning_input

        aligned = await self._alignment_service.align(
            profile=profile_context,
            style_facets=reasoning_input.style_facet_bundle(),
        )

        return reasoning_input.model_copy(
            update={
                "style_advice_facets": aligned.facets.advice_facets,
                "style_image_facets": aligned.facets.image_facets,
                "style_visual_language_facets": aligned.facets.visual_language_facets,
                "style_relation_facets": aligned.facets.relation_facets,
                "profile_alignment_applied": aligned.profile_context_present,
                "profile_alignment_notes": list(aligned.alignment_notes),
                "profile_alignment_filtered_out": list(aligned.filtered_out),
                "profile_facet_weights": dict(aligned.facet_weights),
            },
            deep=True,
        )
