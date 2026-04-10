from time import perf_counter
from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import ChatContextStorePort, EventLogger, GenerationJobScheduler
from app.application.stylist_chat.results.decision_result import DecisionResult, DecisionType
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.models.enums import GenerationStatus

from .command_dispatcher import CommandDispatcher
from .mode_router import ModeRouter


class StylistChatOrchestrator:
    def __init__(
        self,
        *,
        context_store: ChatContextStorePort,
        generation_scheduler: GenerationJobScheduler,
        event_logger: EventLogger,
        command_dispatcher: CommandDispatcher,
        mode_router: ModeRouter,
        generation_request_builder: GenerationRequestBuilder,
    ) -> None:
        self.context_store = context_store
        self.generation_scheduler = generation_scheduler
        self.event_logger = event_logger
        self.command_dispatcher = command_dispatcher
        self.mode_router = mode_router
        self.generation_request_builder = generation_request_builder

    async def handle(self, *, command: ChatCommand) -> DecisionResult:
        started_at = perf_counter()
        session_state_record, context = await self.context_store.load(command.session_id)
        context = await self.generation_scheduler.sync_context(context)
        flow_state_before = context.flow_state

        dispatch = self.command_dispatcher.dispatch(command=command, context=context)
        context = dispatch.context
        session_state_record = await self.context_store.save(
            session_id=command.session_id,
            context=context,
            record=session_state_record,
        )

        handler = self.mode_router.route(dispatch.resolution.active_mode)
        decision = await handler.handle(command=command, context=context)

        if decision.decision_type == DecisionType.ERROR_RECOVERABLE:
            context.flow_state = FlowState.RECOVERABLE_ERROR

        context.last_decision_type = decision.decision_type.value
        context.touch(message_id=command.user_message_id)
        session_state_record = await self.context_store.save(
            session_id=command.session_id,
            context=context,
            record=session_state_record,
        )

        generation_request = self.generation_request_builder.build_schedule_request(
            command=command,
            context=context,
            decision=decision,
        )
        if decision.requires_generation() and generation_request is not None and decision.job_id is None:
            generation_intent = self._prepare_generation_intent(command=command, context=context, decision=decision)
            generation_request.generation_intent = generation_intent
            if context.last_generation_request_key == generation_request.idempotency_key and context.current_job_id:
                decision.job_id = context.current_job_id
            else:
                session_state_record = await self.context_store.save(
                    session_id=command.session_id,
                    context=context,
                    record=session_state_record,
                )
                schedule_result = await self.generation_scheduler.enqueue(generation_request)
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
                    context.last_generation_request_key = generation_request.idempotency_key
                    if decision.generation_payload is not None:
                        context.generation_intent = decision.generation_payload.generation_intent
                        context.last_generation_prompt = decision.generation_payload.prompt
                    context.last_generated_outfit_summary = decision.text_reply
                    context.flow_state = self._flow_state_from_generation_status(schedule_result.status)
                    decision.job_id = schedule_result.job_id
                context.last_decision_type = decision.decision_type.value
                context.touch(message_id=command.user_message_id)
                session_state_record = await self.context_store.save(
                    session_id=command.session_id,
                    context=context,
                    record=session_state_record,
                )

        decision.flow_state = context.flow_state
        decision.context_patch = self.build_context_patch(context)
        decision.telemetry["generation_job_id"] = decision.job_id
        latency_ms = max(int((perf_counter() - started_at) * 1000), 0)
        decision.telemetry["latency_ms"] = latency_ms
        await self.event_logger.emit(
            "stylist_chat_orchestrated",
            {
                "session_id": command.session_id,
                "message_id": command.user_message_id,
                "client_message_id": command.client_message_id,
                "command_id": command.command_id,
                "correlation_id": command.correlation_id,
                "requested_intent": command.requested_intent.value if command.requested_intent else None,
                "active_mode": context.active_mode.value,
                "resolved_mode": context.active_mode.value,
                "flow_state_before": flow_state_before.value,
                "flow_state_after": context.flow_state.value,
                "decision_type": decision.decision_type.value,
                "clarification_kind": context.clarification_kind.value if context.clarification_kind else None,
                "anchor_garment_confidence": decision.telemetry.get("anchor_garment_confidence"),
                "anchor_garment_completeness": decision.telemetry.get("anchor_garment_completeness"),
                "filled_slots": decision.telemetry.get("filled_slots"),
                "missing_slots": decision.telemetry.get("missing_slots"),
                "occasion_completeness": decision.telemetry.get("occasion_completeness"),
                "knowledge_provider_used": decision.telemetry.get("knowledge_provider_used"),
                "provider": decision.telemetry.get("provider"),
                "knowledge_used": decision.telemetry.get("knowledge_items_count", 0),
                "generation_job_id": decision.job_id,
                "style_id": context.current_style_id,
                "fallback_used": decision.telemetry.get("fallback_used", False),
                "latency_ms": latency_ms,
            },
        )
        return decision

    def _prepare_generation_intent(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        decision: DecisionResult,
    ):
        intent_config = {
            ChatMode.GENERAL_ADVICE: ("general_advice", "reasoning_requested_generation", False),
            ChatMode.GARMENT_MATCHING: ("garment_matching", "anchor_garment_is_sufficient_for_generation", True),
            ChatMode.STYLE_EXPLORATION: ("style_exploration", "new_style_direction_selected", True),
            ChatMode.OCCASION_OUTFIT: ("occasion_outfit", "occasion_context_has_required_slots", True),
        }
        trigger, reason, must_generate = intent_config.get(
            context.active_mode,
            (context.active_mode.value, "reasoning_requested_generation", decision.requires_generation()),
        )
        generation_intent = self.generation_request_builder.build_generation_intent(
            mode=context.active_mode,
            trigger=trigger,
            reason=reason,
            must_generate=must_generate,
            source_message_id=command.user_message_id,
        )
        context.generation_intent = generation_intent
        if decision.generation_payload is not None:
            decision.generation_payload.generation_intent = generation_intent
        return generation_intent

    def build_context_patch(self, context: ChatModeContext) -> dict[str, Any]:
        patch: dict[str, Any] = {
            "active_mode": context.active_mode.value,
            "flow_state": context.flow_state.value,
            "last_decision_type": context.last_decision_type,
            "should_auto_generate": context.should_auto_generate,
            "current_job_id": context.current_job_id,
        }
        if context.clarification_kind is not None:
            patch["clarification_kind"] = context.clarification_kind.value
        if context.pending_clarification:
            patch["pending_clarification"] = context.pending_clarification
        if context.anchor_garment is not None:
            patch["anchor_garment"] = context.anchor_garment.model_dump(mode="json", exclude_none=True)
        if context.occasion_context is not None:
            patch["occasion_context"] = context.occasion_context.model_dump(mode="json", exclude_none=True)
        if context.current_style_name:
            patch["current_style_name"] = context.current_style_name
        if context.last_generation_request_key:
            patch["last_generation_request_key"] = context.last_generation_request_key
        return patch

    def _flow_state_from_generation_status(self, status: str) -> FlowState:
        if status == GenerationStatus.PENDING.value:
            return FlowState.GENERATION_QUEUED
        if status in {GenerationStatus.QUEUED.value, GenerationStatus.RUNNING.value}:
            return FlowState.GENERATION_IN_PROGRESS
        if status == GenerationStatus.COMPLETED.value:
            return FlowState.COMPLETED
        return FlowState.RECOVERABLE_ERROR
