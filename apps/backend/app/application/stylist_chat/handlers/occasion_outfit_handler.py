from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import ContextCheckpointWriter
from app.application.stylist_chat.results.decision_result import DecisionResult
from app.application.stylist_chat.use_cases.build_occasion_outfit_brief import BuildOccasionOutfitBriefUseCase
from app.application.stylist_chat.use_cases.continue_occasion_outfit import ContinueOccasionOutfitUseCase
from app.application.stylist_chat.use_cases.start_occasion_outfit import StartOccasionOutfitUseCase
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import FlowState

from .base import BaseChatModeHandler


class OccasionOutfitHandler(BaseChatModeHandler):
    def __init__(
        self,
        *,
        start_use_case: StartOccasionOutfitUseCase,
        continue_use_case: ContinueOccasionOutfitUseCase,
        build_outfit_brief_use_case: BuildOccasionOutfitBriefUseCase,
        context_checkpoint_writer: ContextCheckpointWriter | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.start_use_case = start_use_case
        self.continue_use_case = continue_use_case
        self.build_outfit_brief_use_case = build_outfit_brief_use_case
        self.context_checkpoint_writer = context_checkpoint_writer

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

        reuse_existing_occasion = (
            context.occasion_context is not None
            and context.occasion_context.is_sufficient_for_generation
            and (
                command.source in {"visualization_cta", "explicit_visual_request"}
                or self.generation_request_builder.explicitly_requests_generation(command.normalized_message())
            )
        )
        if reuse_existing_occasion:
            assessment = self.continue_use_case.update_occasion_context.completeness_evaluator.evaluate(
                context.occasion_context
            )
            continuation = type(
                "OccasionContinuationReuse",
                (),
                {
                    "occasion_context": context.occasion_context,
                    "assessment": assessment,
                },
            )()
        else:
            continuation = await self.continue_use_case.execute(command=command, context=context)
        if context.flow_state == FlowState.AWAITING_OCCASION_CLARIFICATION:
            decision = self.generation_request_builder.build_clarification_decision(
                context=context,
                text=context.pending_clarification or entry_prompt,
            )
            decision.telemetry.update(
                {
                    "occasion_completeness": continuation.assessment.completeness_score,
                    "filled_slots": continuation.assessment.filled_slots,
                    "missing_slots": continuation.assessment.missing_slots,
                    "knowledge_provider_used": "occasion_clarification_policy",
                }
            )
            return decision

        build_result = await self.build_outfit_brief_use_case.execute(
            command=command,
            context=context,
            occasion_context=continuation.occasion_context,
        )
        context.flow_state = FlowState.READY_FOR_GENERATION
        decision = await self.run_reasoning(
            command=command.model_copy(
                update={
                    "message": continuation.occasion_context.raw_user_texts[-1]
                    if continuation.occasion_context.raw_user_texts
                    else command.message,
                }
            ),
            context=context,
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=continuation.occasion_context,
            anti_repeat_constraints=None,
            knowledge_mode="occasion_outfit",
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
                "occasion_completeness": continuation.assessment.completeness_score,
                "filled_slots": continuation.assessment.filled_slots,
                "missing_slots": continuation.assessment.missing_slots,
                "knowledge_provider_used": build_result.knowledge_result.source,
            }
        )
        return decision
