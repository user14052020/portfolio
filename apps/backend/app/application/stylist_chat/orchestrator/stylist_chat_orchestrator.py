from time import perf_counter
from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import (
    ChatContextStorePort,
    EventLogger,
    GenerationJobScheduler,
    MetricsRecorder,
)
from app.application.stylist_chat.results.decision_result import DecisionResult, DecisionType
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, ClarificationKind, FlowState
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
        metrics_recorder: MetricsRecorder,
        command_dispatcher: CommandDispatcher,
        mode_router: ModeRouter,
        generation_request_builder: GenerationRequestBuilder,
    ) -> None:
        self.context_store = context_store
        self.generation_scheduler = generation_scheduler
        self.event_logger = event_logger
        self.metrics_recorder = metrics_recorder
        self.command_dispatcher = command_dispatcher
        self.mode_router = mode_router
        self.generation_request_builder = generation_request_builder

    async def handle(self, *, command: ChatCommand) -> DecisionResult:
        started_at = perf_counter()
        session_state_record, context = await self.context_store.load(command.session_id)
        context = await self.generation_scheduler.sync_context(context)
        flow_state_before = context.flow_state
        clarification_kind_before = context.clarification_kind

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
        decision.context_patch = {
            **self.build_context_patch(context),
            **decision.context_patch,
        }
        decision.telemetry["generation_job_id"] = decision.job_id
        latency_ms = max(int((perf_counter() - started_at) * 1000), 0)
        decision.telemetry["latency_ms"] = latency_ms
        await self._record_metrics(
            command=command,
            context=context,
            decision=decision,
            flow_state_before=flow_state_before,
            clarification_kind_before=clarification_kind_before,
        )
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
                "knowledge_query_hash": decision.telemetry.get("knowledge_query_hash"),
                "knowledge_bundle_hash": decision.telemetry.get("knowledge_bundle_hash"),
                "retrieved_style_cards_count": decision.telemetry.get("retrieved_style_cards_count"),
                "retrieved_color_cards_count": decision.telemetry.get("retrieved_color_cards_count"),
                "retrieved_history_cards_count": decision.telemetry.get("retrieved_history_cards_count"),
                "retrieved_tailoring_cards_count": decision.telemetry.get("retrieved_tailoring_cards_count"),
                "retrieved_material_cards_count": decision.telemetry.get("retrieved_material_cards_count"),
                "retrieved_flatlay_cards_count": decision.telemetry.get("retrieved_flatlay_cards_count"),
                "generation_job_id": decision.job_id,
                "style_id": context.current_style_id,
                "style_name": decision.telemetry.get("style_name") or context.current_style_name,
                "style_history_size": decision.telemetry.get("style_history_size"),
                "semantic_constraints_hash": decision.telemetry.get("semantic_constraints_hash"),
                "visual_constraints_hash": decision.telemetry.get("visual_constraints_hash"),
                "brief_hash": decision.telemetry.get("brief_hash"),
                "compiled_prompt_hash": decision.telemetry.get("compiled_prompt_hash"),
                "diversity_constraints_hash": decision.telemetry.get("diversity_constraints_hash"),
                "knowledge_cards_count": decision.telemetry.get("knowledge_cards_count"),
                "validation_errors_count": decision.telemetry.get("validation_errors_count"),
                "palette": decision.telemetry.get("palette"),
                "hero_garments": decision.telemetry.get("hero_garments"),
                "composition_type": decision.telemetry.get("composition_type"),
                "visual_preset": decision.telemetry.get("visual_preset"),
                "workflow_name": decision.telemetry.get("workflow_name"),
                "workflow_version": decision.telemetry.get("workflow_version"),
                "layout_archetype": decision.telemetry.get("layout_archetype"),
                "background_family": decision.telemetry.get("background_family"),
                "object_count_range": decision.telemetry.get("object_count_range"),
                "spacing_density": decision.telemetry.get("spacing_density"),
                "camera_distance": decision.telemetry.get("camera_distance"),
                "shadow_hardness": decision.telemetry.get("shadow_hardness"),
                "anchor_garment_centrality": decision.telemetry.get("anchor_garment_centrality"),
                "practical_coherence": decision.telemetry.get("practical_coherence"),
                "fallback_used": decision.telemetry.get("fallback_used", False),
                "latency_ms": latency_ms,
            },
        )
        return decision

    async def _record_metrics(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        decision: DecisionResult,
        flow_state_before: FlowState,
        clarification_kind_before: ClarificationKind | None,
    ) -> None:
        knowledge_counts = [
            int(decision.telemetry.get("retrieved_style_cards_count") or 0),
            int(decision.telemetry.get("retrieved_color_cards_count") or 0),
            int(decision.telemetry.get("retrieved_history_cards_count") or 0),
            int(decision.telemetry.get("retrieved_tailoring_cards_count") or 0),
            int(decision.telemetry.get("retrieved_material_cards_count") or 0),
            int(decision.telemetry.get("retrieved_flatlay_cards_count") or 0),
        ]
        if decision.telemetry.get("knowledge_query_hash"):
            knowledge_tags = {
                "mode": context.active_mode.value,
                "decision_type": decision.decision_type.value,
            }
            await self.metrics_recorder.increment("knowledge_retrieval_requests", tags=knowledge_tags)
            await self.metrics_recorder.observe(
                "knowledge_bundle_size",
                value=float(sum(knowledge_counts)),
                tags=knowledge_tags,
            )
            if sum(knowledge_counts) == 0:
                await self.metrics_recorder.increment("knowledge_empty_bundle", tags=knowledge_tags)

        if decision.job_id is not None and decision.telemetry.get("workflow_name"):
            visual_tags: dict[str, Any] = {
                "mode": context.active_mode.value,
                "workflow_name": decision.telemetry.get("workflow_name"),
                "visual_preset": decision.telemetry.get("visual_preset"),
                "layout_archetype": decision.telemetry.get("layout_archetype"),
                "background_family": decision.telemetry.get("background_family"),
            }
            await self.metrics_recorder.increment("generation_runs_by_workflow", tags=visual_tags)
            await self.metrics_recorder.increment("generation_runs_by_visual_preset", tags=visual_tags)

        if context.active_mode == ChatMode.STYLE_EXPLORATION:
            style_tags: dict[str, Any] = {
                "mode": context.active_mode.value,
                "decision_type": decision.decision_type.value,
                "flow_state_before": flow_state_before.value,
                "flow_state_after": context.flow_state.value,
                "visual_preset": decision.telemetry.get("visual_preset"),
            }
            if command.command_step == "start":
                await self.metrics_recorder.increment("style_exploration_flows_started", tags=style_tags)
            if decision.job_id is not None:
                await self.metrics_recorder.increment("style_exploration_flows_ending_in_generation", tags=style_tags)
                await self.metrics_recorder.increment("generation_success_rate_per_visual_preset", tags=style_tags)
            for metric_name in (
                "palette_repeat_rate",
                "hero_garment_repeat_rate",
                "silhouette_repeat_rate",
                "composition_repeat_rate",
                "semantic_diversity_score",
                "visual_diversity_score",
            ):
                raw_value = decision.telemetry.get(metric_name)
                if isinstance(raw_value, (int, float)):
                    await self.metrics_recorder.observe(metric_name, value=float(raw_value), tags=style_tags)
            return

        if context.active_mode != ChatMode.OCCASION_OUTFIT:
            return

        tags: dict[str, Any] = {
            "mode": context.active_mode.value,
            "decision_type": decision.decision_type.value,
            "flow_state_before": flow_state_before.value,
            "flow_state_after": context.flow_state.value,
        }
        if context.clarification_kind is not None:
            tags["clarification_kind"] = context.clarification_kind.value

        if command.command_step == "start":
            await self.metrics_recorder.increment("occasion_flow_started", tags=tags)

        completeness = decision.telemetry.get("occasion_completeness")
        if isinstance(completeness, (int, float)):
            await self.metrics_recorder.observe(
                "occasion_slot_completeness",
                value=float(completeness),
                tags=tags,
            )

        if decision.decision_type == DecisionType.CLARIFICATION_REQUIRED:
            await self.metrics_recorder.increment("occasion_flow_clarification_steps", tags=tags)
            if clarification_kind_before is not None and clarification_kind_before == context.clarification_kind:
                await self.metrics_recorder.increment("occasion_repeated_missing_slot", tags=tags)

        if context.occasion_context is not None and context.occasion_context.is_sufficient_for_generation:
            await self.metrics_recorder.increment("occasion_flow_ready_for_generation", tags=tags)

        if decision.job_id is not None:
            await self.metrics_recorder.increment("occasion_flow_ended_in_generation", tags=tags)
            await self.metrics_recorder.increment("occasion_generation_success_after_readiness", tags=tags)
            await self.metrics_recorder.observe(
                "occasion_clarifications_before_generation",
                value=float(context.clarification_attempts),
                tags=tags,
            )

        if decision.decision_type == DecisionType.ERROR_RECOVERABLE:
            await self.metrics_recorder.increment("occasion_flow_recoverable_failures", tags=tags)
            if decision.error_code == "generation_enqueue_failed":
                await self.metrics_recorder.increment("occasion_queue_failures", tags=tags)

        if (
            context.occasion_context is not None
            and context.occasion_context.is_sufficient_for_generation
            and not decision.requires_generation()
            and decision.decision_type not in {DecisionType.ERROR_RECOVERABLE, DecisionType.ERROR_HARD}
        ):
            await self.metrics_recorder.increment("occasion_silent_failures", tags=tags)

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
        if context.current_style_id:
            patch["current_style_id"] = context.current_style_id
        if context.last_retrieved_knowledge_refs:
            patch["last_retrieved_knowledge_refs"] = [dict(item) for item in context.last_retrieved_knowledge_refs]
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
