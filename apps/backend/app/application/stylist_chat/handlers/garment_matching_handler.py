from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import GenerationJobScheduler
from app.application.stylist_chat.results.decision_result import DecisionResult
from app.application.stylist_chat.use_cases.build_garment_outfit_brief import BuildGarmentOutfitBriefUseCase
from app.application.stylist_chat.use_cases.continue_garment_matching import ContinueGarmentMatchingUseCase
from app.application.stylist_chat.use_cases.start_garment_matching import StartGarmentMatchingUseCase
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import FlowState
from app.models.enums import GenerationStatus

from .base import BaseChatModeHandler


class GarmentMatchingHandler(BaseChatModeHandler):
    def __init__(
        self,
        *,
        start_use_case: StartGarmentMatchingUseCase,
        continue_use_case: ContinueGarmentMatchingUseCase,
        build_outfit_brief_use_case: BuildGarmentOutfitBriefUseCase,
        generation_scheduler: GenerationJobScheduler,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.start_use_case = start_use_case
        self.continue_use_case = continue_use_case
        self.build_outfit_brief_use_case = build_outfit_brief_use_case
        self.generation_scheduler = generation_scheduler

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
            must_generate=True,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
            knowledge_mode="garment_matching",
            style_history_used=False,
            structured_outfit_brief=build_result.compiled_brief,
            knowledge_result_override=build_result.knowledge_result,
        )
        context.last_generated_outfit_summary = decision.text_reply
        if decision.generation_payload is not None:
            context.last_generation_prompt = decision.generation_payload.prompt
            generation_intent = self.generation_request_builder.build_generation_intent(
                mode=context.active_mode,
                trigger="garment_matching",
                reason="anchor_garment_is_sufficient_for_generation",
                must_generate=True,
                source_message_id=command.user_message_id,
            )
            context.generation_intent = generation_intent
            decision.generation_payload.generation_intent = generation_intent
            schedule_request = self.generation_request_builder.build_schedule_request(
                command=command,
                context=context,
                decision=decision,
            )
            if schedule_request is not None:
                if context.last_generation_request_key == schedule_request.idempotency_key and context.current_job_id:
                    decision.job_id = context.current_job_id
                    context.flow_state = self._flow_state_from_generation_status(GenerationStatus.PENDING.value)
                else:
                    schedule_result = await self.generation_scheduler.enqueue(schedule_request)
                    if schedule_result.blocked_by_active_job:
                        original_telemetry = dict(decision.telemetry)
                        context.current_job_id = schedule_result.job_id
                        context.flow_state = self._flow_state_from_generation_status(schedule_result.status)
                        decision = self.generation_request_builder.build_active_job_notice(
                            context=context,
                            locale=command.locale,
                        )
                        decision.telemetry.update(original_telemetry)
                    elif self._flow_state_from_generation_status(schedule_result.status) == FlowState.RECOVERABLE_ERROR:
                        original_telemetry = dict(decision.telemetry)
                        decision = self.generation_request_builder.build_recoverable_error(
                            context=context,
                            locale=command.locale,
                            error_code="generation_enqueue_failed",
                        )
                        context.current_job_id = None
                        context.flow_state = FlowState.RECOVERABLE_ERROR
                        decision.telemetry.update(original_telemetry)
                    else:
                        context.current_job_id = schedule_result.job_id
                        context.last_generation_request_key = schedule_request.idempotency_key
                        context.flow_state = self._flow_state_from_generation_status(schedule_result.status)
                        decision.job_id = schedule_result.job_id
        decision.telemetry.update(
            {
                "anchor_garment_confidence": continuation.anchor_garment.confidence,
                "anchor_garment_completeness": continuation.anchor_garment.completeness_score,
                "knowledge_provider_used": build_result.knowledge_result.source,
            }
        )
        return decision

    def _flow_state_from_generation_status(self, status: str) -> FlowState:
        if status == GenerationStatus.PENDING.value:
            return FlowState.GENERATION_QUEUED
        if status in {GenerationStatus.QUEUED.value, GenerationStatus.RUNNING.value}:
            return FlowState.GENERATION_IN_PROGRESS
        if status == GenerationStatus.COMPLETED.value:
            return FlowState.COMPLETED
        return FlowState.RECOVERABLE_ERROR
