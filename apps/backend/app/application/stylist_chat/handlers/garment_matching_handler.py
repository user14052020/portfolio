from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionResult
from app.application.stylist_chat.use_cases.build_garment_outfit_brief import BuildGarmentOutfitBriefUseCase
from app.application.stylist_chat.use_cases.continue_garment_matching import ContinueGarmentMatchingUseCase
from app.application.stylist_chat.use_cases.start_garment_matching import StartGarmentMatchingUseCase
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import FlowState

from .base import BaseChatModeHandler


class GarmentMatchingHandler(BaseChatModeHandler):
    def __init__(
        self,
        *,
        start_use_case: StartGarmentMatchingUseCase,
        continue_use_case: ContinueGarmentMatchingUseCase,
        build_outfit_brief_use_case: BuildGarmentOutfitBriefUseCase,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.start_use_case = start_use_case
        self.continue_use_case = continue_use_case
        self.build_outfit_brief_use_case = build_outfit_brief_use_case

    async def handle(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        entry_prompt = context.pending_clarification or ""
        if command.command_step == "start":
            entry_prompt = self.start_use_case.execute(context=context, locale=command.locale)
            return self.generation_request_builder.build_clarification_decision(
                context=context,
                text=entry_prompt,
            )
        if context.flow_state in {FlowState.IDLE, FlowState.COMPLETED, FlowState.RECOVERABLE_ERROR}:
            entry_prompt = self.start_use_case.execute(context=context, locale=command.locale)

        reuse_existing_anchor = (
            context.anchor_garment is not None
            and context.anchor_garment.is_sufficient_for_generation
            and (
                command.source in {"visualization_cta", "explicit_visual_request"}
                or self.generation_request_builder.explicitly_requests_generation(command.normalized_message())
            )
        )
        if reuse_existing_anchor:
            continuation = type(
                "GarmentContinuationReuse",
                (),
                {"anchor_garment": context.anchor_garment},
            )()
        else:
            continuation = await self.continue_use_case.execute(command=command, context=context)
        if context.flow_state == FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION:
            decision = self.generation_request_builder.build_clarification_decision(
                context=context,
                text=context.pending_clarification or entry_prompt,
            )
            decision.telemetry.update(
                {
                    "anchor_garment_confidence": continuation.anchor_garment.confidence,
                    "anchor_garment_completeness": continuation.anchor_garment.completeness_score,
                    "knowledge_provider_used": "clarification_policy",
                }
            )
            return decision

        build_result = await self.build_outfit_brief_use_case.execute(
            command=command,
            context=context,
            garment=continuation.anchor_garment,
        )
        context.flow_state = FlowState.READY_FOR_GENERATION
        decision = await self.run_reasoning(
            command=command.model_copy(
                update={
                    "message": continuation.anchor_garment.raw_user_text or command.message,
                }
            ),
            context=context,
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
            knowledge_mode="garment_matching",
            style_history_used=False,
            structured_outfit_brief=build_result.compiled_brief,
            knowledge_result_override=build_result.knowledge_result,
            knowledge_bundle_override=build_result.knowledge_bundle,
        )
        context.last_generated_outfit_summary = decision.text_reply
        if decision.generation_payload is not None:
            context.last_generation_prompt = decision.generation_payload.prompt
        decision.telemetry.update(
            {
                "anchor_garment_confidence": continuation.anchor_garment.confidence,
                "anchor_garment_completeness": continuation.anchor_garment.completeness_score,
                "knowledge_provider_used": build_result.knowledge_result.source,
            }
        )
        return decision
