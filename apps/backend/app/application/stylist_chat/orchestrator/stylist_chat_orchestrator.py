from time import perf_counter
from typing import Any

from app.application.product_behavior.services.post_action_conversation_policy import PostActionConversationPolicy
from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import (
    ChatContextStorePort,
    ConversationRoutingResult,
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
        post_action_conversation_policy: PostActionConversationPolicy,
    ) -> None:
        self.context_store = context_store
        self.generation_scheduler = generation_scheduler
        self.event_logger = event_logger
        self.metrics_recorder = metrics_recorder
        self.command_dispatcher = command_dispatcher
        self.mode_router = mode_router
        self.generation_request_builder = generation_request_builder
        self.post_action_conversation_policy = post_action_conversation_policy

    async def handle(self, *, command: ChatCommand) -> DecisionResult:
        started_at = perf_counter()
        session_state_record, context = await self.context_store.load(command.session_id)
        context = await self.generation_scheduler.sync_context(context)
        active_mode_before = context.active_mode
        flow_state_before = context.flow_state
        clarification_kind_before = context.clarification_kind

        dispatch = await self.command_dispatcher.dispatch(command=command, context=context)
        context = dispatch.context
        await self._emit_routing_event(
            command=command,
            routing=dispatch.routing,
            active_mode_before=active_mode_before,
            flow_state_before=flow_state_before,
            active_mode_after=context.active_mode,
            flow_state_after=context.flow_state,
        )
        session_state_record = await self.context_store.save(
            session_id=command.session_id,
            context=context,
            record=session_state_record,
        )

        handler = self.mode_router.route(dispatch.resolution.active_mode)
        decision = await handler.handle(command=command, context=context)

        if decision.decision_type == DecisionType.ERROR_RECOVERABLE:
            context.flow_state = FlowState.RECOVERABLE_ERROR

        context.visualization_offer = decision.visualization_offer
        context = self.post_action_conversation_policy.apply(
            context=context,
            decision=decision,
        )
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
                elif schedule_result.notice_text:
                    original_telemetry = dict(decision.telemetry)
                    context.current_job_id = None
                    context.flow_state = FlowState.COMPLETED
                    decision = self.generation_request_builder.downgrade_generation_to_text_only(
                        decision=decision,
                        context=context,
                        notice_text=schedule_result.notice_text,
                        replace_text=schedule_result.notice_replaces_text,
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
                    context.visualization_offer = None
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
                "routing_provider": dispatch.routing.provider,
                "routing_mode": dispatch.routing.decision.mode.value,
                "routing_confidence": dispatch.routing.decision.confidence,
                "routing_needs_clarification": dispatch.routing.decision.needs_clarification,
                "routing_missing_slots": list(dispatch.routing.decision.missing_slots),
                "routing_generation_intent": dispatch.routing.decision.generation_intent,
                "routing_continue_existing_flow": dispatch.routing.decision.continue_existing_flow,
                "routing_should_reset_to_general": dispatch.routing.decision.should_reset_to_general,
                "routing_reasoning_depth": dispatch.routing.decision.reasoning_depth.value,
                "routing_retrieval_profile": dispatch.routing.decision.retrieval_profile,
                "routing_used_fallback": dispatch.routing.used_fallback,
                "routing_failure_reason": (
                    dispatch.routing.failure_reason.value if dispatch.routing.failure_reason else None
                ),
                "routing_fallback_rule": dispatch.routing.fallback_rule,
                "routing_validation_errors_count": len(dispatch.routing.validation_errors),
                "routing_stripped_fields_count": len(dispatch.routing.stripped_fields),
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
                "reasoning_pipeline_used": decision.telemetry.get("reasoning_pipeline_used", False),
                "reasoning_response_type": decision.telemetry.get("reasoning_response_type"),
                "reasoning_retrieval_profile": decision.telemetry.get("reasoning_retrieval_profile"),
                "reasoning_used_providers": decision.telemetry.get("reasoning_used_providers"),
                "reasoning_knowledge_query_mode": decision.telemetry.get("knowledge_query_mode"),
                "reasoning_knowledge_provider_count": decision.telemetry.get("knowledge_provider_count"),
                "reasoning_knowledge_providers_used": decision.telemetry.get("knowledge_providers_used"),
                "reasoning_knowledge_cards_per_provider": decision.telemetry.get(
                    "knowledge_cards_per_provider"
                ),
                "reasoning_knowledge_empty_providers": decision.telemetry.get(
                    "knowledge_empty_providers"
                ),
                "reasoning_knowledge_provider_latency_ms": decision.telemetry.get(
                    "knowledge_provider_latency_ms"
                ),
                "reasoning_knowledge_duplicate_cards_filtered_count": decision.telemetry.get(
                    "knowledge_duplicate_cards_filtered_count"
                ),
                "reasoning_knowledge_cards_filtered_out_count": decision.telemetry.get(
                    "knowledge_cards_filtered_out_count"
                ),
                "reasoning_knowledge_ranking_summary": decision.telemetry.get(
                    "knowledge_ranking_summary"
                ),
                "reasoning_style_provider_projected_cards_count": decision.telemetry.get(
                    "style_provider_projected_cards_count"
                ),
                "reasoning_style_provider_knowledge_types": decision.telemetry.get(
                    "style_provider_knowledge_types"
                ),
                "reasoning_style_provider_projection_versions": decision.telemetry.get(
                    "style_provider_projection_versions"
                ),
                "reasoning_style_provider_parser_versions": decision.telemetry.get(
                    "style_provider_parser_versions"
                ),
                "reasoning_style_provider_low_richness_styles": decision.telemetry.get(
                    "style_provider_low_richness_styles"
                ),
                "reasoning_style_provider_legacy_summary_fallback_styles": decision.telemetry.get(
                    "style_provider_legacy_summary_fallback_styles"
                ),
                "reasoning_style_facets_count": decision.telemetry.get("reasoning_style_facets_count"),
                "reasoning_style_advice_facets_count": decision.telemetry.get(
                    "reasoning_style_advice_facets_count"
                ),
                "reasoning_style_image_facets_count": decision.telemetry.get(
                    "reasoning_style_image_facets_count"
                ),
                "reasoning_style_visual_language_facets_count": decision.telemetry.get(
                    "reasoning_style_visual_language_facets_count"
                ),
                "reasoning_style_relation_facets_count": decision.telemetry.get(
                    "reasoning_style_relation_facets_count"
                ),
                "reasoning_style_semantic_fragments_count": decision.telemetry.get(
                    "reasoning_style_semantic_fragments_count"
                ),
                "reasoning_profile_alignment_applied": decision.telemetry.get(
                    "reasoning_profile_alignment_applied"
                ),
                "reasoning_profile_context_present": decision.telemetry.get(
                    "reasoning_profile_context_present"
                ),
                "reasoning_profile_context_source": decision.telemetry.get(
                    "reasoning_profile_context_source"
                ),
                "reasoning_profile_fields_count": decision.telemetry.get(
                    "reasoning_profile_fields_count"
                ),
                "reasoning_profile_alignment_filtered_count": decision.telemetry.get(
                    "reasoning_profile_alignment_filtered_count"
                ),
                "reasoning_profile_alignment_boosted_categories": decision.telemetry.get(
                    "reasoning_profile_alignment_boosted_categories"
                ),
                "reasoning_profile_alignment_removed_item_types": decision.telemetry.get(
                    "reasoning_profile_alignment_removed_item_types"
                ),
                "reasoning_profile_completeness_state": decision.telemetry.get(
                    "reasoning_profile_completeness_state"
                ),
                "reasoning_profile_clarification_decision": decision.telemetry.get(
                    "reasoning_profile_clarification_decision"
                ),
                "reasoning_profile_clarification_required": decision.telemetry.get(
                    "reasoning_profile_clarification_required"
                ),
                "reasoning_clarification_required": decision.telemetry.get(
                    "reasoning_clarification_required"
                ),
                "reasoning_brief_built": decision.telemetry.get("reasoning_brief_built"),
                "reasoning_cta_offered": decision.telemetry.get("reasoning_cta_offered"),
                "reasoning_generation_ready": decision.telemetry.get("reasoning_generation_ready"),
                "reasoning_profile_derived_constraints_count": decision.telemetry.get(
                    "reasoning_profile_derived_constraints_count"
                ),
                "reasoning_voice_payload_ready": decision.telemetry.get("reasoning_voice_payload_ready"),
                "reasoning_voice_mode": decision.telemetry.get("reasoning_voice_mode"),
                "reasoning_voice_response_type": decision.telemetry.get(
                    "reasoning_voice_response_type"
                ),
                "reasoning_voice_desired_depth": decision.telemetry.get(
                    "reasoning_voice_desired_depth"
                ),
                "reasoning_voice_knowledge_density": decision.telemetry.get(
                    "reasoning_voice_knowledge_density"
                ),
                "reasoning_voice_should_be_brief": decision.telemetry.get(
                    "reasoning_voice_should_be_brief"
                ),
                "reasoning_voice_profile_context_present": decision.telemetry.get(
                    "reasoning_voice_profile_context_present"
                ),
                "reasoning_voice_tone_profile": decision.telemetry.get(
                    "reasoning_voice_tone_profile"
                ),
                "reasoning_voice_layers_used": decision.telemetry.get(
                    "reasoning_voice_layers_used"
                ),
                "reasoning_voice_historical_used": decision.telemetry.get(
                    "reasoning_voice_historical_used"
                ),
                "reasoning_voice_color_poetics_used": decision.telemetry.get(
                    "reasoning_voice_color_poetics_used"
                ),
                "reasoning_voice_brevity_level": decision.telemetry.get(
                    "reasoning_voice_brevity_level"
                ),
                "reasoning_voice_cta_present": decision.telemetry.get(
                    "reasoning_voice_cta_present"
                ),
                "reasoning_voice_cta_style": decision.telemetry.get(
                    "reasoning_voice_cta_style"
                ),
                "reasoning_voice_text_length": decision.telemetry.get(
                    "reasoning_voice_text_length"
                ),
                "reasoning_generation_handoff_ready": decision.telemetry.get(
                    "reasoning_generation_handoff_ready"
                ),
                "reasoning_generation_blocked_reason": decision.telemetry.get(
                    "reasoning_generation_blocked_reason"
                ),
                "reasoning_cta_decision_reason": decision.telemetry.get("cta_decision_reason"),
                "reasoning_cta_blocked_reasons": decision.telemetry.get("cta_blocked_reasons"),
                "reasoning_cta_confidence_score": decision.telemetry.get("cta_confidence_score"),
                "reasoning_profile_signals_sufficient": decision.telemetry.get(
                    "profile_signals_sufficient"
                ),
                "reasoning_is_mostly_advisory": decision.telemetry.get(
                    "reasoning_is_mostly_advisory"
                ),
                "reasoning_visual_intent_signal_present": decision.telemetry.get(
                    "visual_intent_signal_present"
                ),
                "reasoning_image_context_strength": decision.telemetry.get("image_context_strength"),
                "reasoning_style_logic_points_count": decision.telemetry.get(
                    "style_logic_points_count"
                ),
                "reasoning_visual_language_points_count": decision.telemetry.get(
                    "visual_language_points_count"
                ),
                "reasoning_historical_note_candidates_count": decision.telemetry.get(
                    "historical_note_candidates_count"
                ),
                "reasoning_styling_rule_candidates_count": decision.telemetry.get(
                    "styling_rule_candidates_count"
                ),
                "reasoning_anti_repeat_related_style_selected": decision.telemetry.get(
                    "anti_repeat_related_style_selected"
                ),
                "reasoning_anti_repeat_hero_garments_avoided_count": decision.telemetry.get(
                    "anti_repeat_hero_garments_avoided_count"
                ),
                "reasoning_anti_repeat_accessories_avoided_count": decision.telemetry.get(
                    "anti_repeat_accessories_avoided_count"
                ),
                "reasoning_anti_repeat_composition_cues_avoided_count": decision.telemetry.get(
                    "anti_repeat_composition_cues_avoided_count"
                ),
                "reasoning_anti_repeat_visual_motifs_avoided_count": decision.telemetry.get(
                    "anti_repeat_visual_motifs_avoided_count"
                ),
                "reasoning_voice_style_logic_points_count": decision.telemetry.get(
                    "reasoning_voice_style_logic_points_count"
                ),
                "reasoning_voice_visual_language_points_count": decision.telemetry.get(
                    "reasoning_voice_visual_language_points_count"
                ),
                "latency_ms": latency_ms,
            },
        )
        return decision

    async def _emit_routing_event(
        self,
        *,
        command: ChatCommand,
        routing: ConversationRoutingResult,
        active_mode_before: ChatMode,
        flow_state_before: FlowState,
        active_mode_after: ChatMode,
        flow_state_after: FlowState,
    ) -> None:
        routing_input_payload = routing.routing_input.model_dump(
            mode="json",
            exclude={"user_message", "recent_messages"},
        )
        routing_input_payload["recent_messages_count"] = len(routing.routing_input.recent_messages)
        routing_context_payload = routing.routing_context.model_dump(
            mode="json",
            exclude={"recent_messages"},
        )
        routing_context_payload["recent_messages_count"] = len(routing.routing_context.recent_messages)

        await self.event_logger.emit(
            "stylist_chat_routed",
            {
                "session_id": command.session_id,
                "message_id": command.user_message_id,
                "client_message_id": command.client_message_id,
                "command_id": command.command_id,
                "correlation_id": command.correlation_id,
                "requested_intent": command.requested_intent.value if command.requested_intent else None,
                "active_mode_before": active_mode_before.value,
                "flow_state_before": flow_state_before.value,
                "active_mode_after": active_mode_after.value,
                "flow_state_after": flow_state_after.value,
                "provider": routing.provider,
                "routing_mode": routing.decision.mode.value,
                "confidence": routing.decision.confidence,
                "needs_clarification": routing.decision.needs_clarification,
                "missing_slots": list(routing.decision.missing_slots),
                "generation_intent": routing.decision.generation_intent,
                "continue_existing_flow": routing.decision.continue_existing_flow,
                "should_reset_to_general": routing.decision.should_reset_to_general,
                "reasoning_depth": routing.decision.reasoning_depth.value,
                "retrieval_profile": routing.decision.retrieval_profile,
                "requires_style_retrieval": routing.decision.requires_style_retrieval,
                "requires_historical_layer": routing.decision.requires_historical_layer,
                "requires_stylist_guidance": routing.decision.requires_stylist_guidance,
                "notes": routing.decision.notes,
                "used_fallback": routing.used_fallback,
                "failure_reason": routing.failure_reason.value if routing.failure_reason else None,
                "fallback_rule": routing.fallback_rule,
                "validation_errors": list(routing.validation_errors),
                "stripped_fields": list(routing.stripped_fields),
                "normalized_payload": dict(routing.normalized_payload),
                "raw_content_present": bool(routing.raw_content),
                "raw_content_length": len(routing.raw_content or ""),
                "routing_input": routing_input_payload,
                "routing_context": routing_context_payload,
            },
        )

    async def _record_metrics(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        decision: DecisionResult,
        flow_state_before: FlowState,
        clarification_kind_before: ClarificationKind | None,
    ) -> None:
        if decision.telemetry.get("reasoning_pipeline_used"):
            reasoning_tags: dict[str, Any] = {
                "mode": context.active_mode.value,
                "decision_type": decision.decision_type.value,
                "response_type": decision.telemetry.get("reasoning_response_type"),
                "retrieval_profile": decision.telemetry.get("reasoning_retrieval_profile"),
                "voice_mode": decision.telemetry.get("reasoning_voice_mode") or "unknown",
                "voice_desired_depth": decision.telemetry.get("reasoning_voice_desired_depth")
                or "unknown",
                "voice_brevity_level": decision.telemetry.get("reasoning_voice_brevity_level")
                or "unknown",
                "profile_alignment_applied": str(
                    bool(decision.telemetry.get("reasoning_profile_alignment_applied"))
                ).lower(),
                "profile_context_present": str(
                    bool(decision.telemetry.get("reasoning_profile_context_present"))
                ).lower(),
                "profile_context_source": decision.telemetry.get("reasoning_profile_context_source") or "none",
            }
            await self.metrics_recorder.increment("reasoning_pipeline_runs", tags=reasoning_tags)
            await self.metrics_recorder.observe(
                "reasoning_style_facets_count",
                value=float(decision.telemetry.get("reasoning_style_facets_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_knowledge_provider_count",
                value=float(decision.telemetry.get("knowledge_provider_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_knowledge_empty_providers_count",
                value=float(len(decision.telemetry.get("knowledge_empty_providers") or [])),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_knowledge_cards_filtered_out_count",
                value=float(decision.telemetry.get("knowledge_cards_filtered_out_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_style_provider_projected_cards_count",
                value=float(decision.telemetry.get("style_provider_projected_cards_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_style_provider_low_richness_styles_count",
                value=float(len(decision.telemetry.get("style_provider_low_richness_styles") or [])),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_profile_fields_count",
                value=float(decision.telemetry.get("reasoning_profile_fields_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_profile_alignment_filtered_count",
                value=float(decision.telemetry.get("reasoning_profile_alignment_filtered_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_profile_alignment_boosted_categories_count",
                value=float(
                    len(decision.telemetry.get("reasoning_profile_alignment_boosted_categories") or [])
                ),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_profile_alignment_removed_item_types_count",
                value=float(
                    len(decision.telemetry.get("reasoning_profile_alignment_removed_item_types") or [])
                ),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_profile_derived_constraints_count",
                value=float(decision.telemetry.get("reasoning_profile_derived_constraints_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_voice_style_logic_points_count",
                value=float(decision.telemetry.get("reasoning_voice_style_logic_points_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_voice_visual_language_points_count",
                value=float(decision.telemetry.get("reasoning_voice_visual_language_points_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_voice_text_length",
                value=float(decision.telemetry.get("reasoning_voice_text_length") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_voice_layers_used_count",
                value=float(len(decision.telemetry.get("reasoning_voice_layers_used") or [])),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_style_logic_points_count",
                value=float(decision.telemetry.get("style_logic_points_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_visual_language_points_count",
                value=float(decision.telemetry.get("visual_language_points_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_historical_note_candidates_count",
                value=float(decision.telemetry.get("historical_note_candidates_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_styling_rule_candidates_count",
                value=float(decision.telemetry.get("styling_rule_candidates_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_cta_confidence_score",
                value=float(decision.telemetry.get("cta_confidence_score") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_image_context_strength",
                value=float(decision.telemetry.get("image_context_strength") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_anti_repeat_hero_garments_avoided_count",
                value=float(decision.telemetry.get("anti_repeat_hero_garments_avoided_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_anti_repeat_accessories_avoided_count",
                value=float(decision.telemetry.get("anti_repeat_accessories_avoided_count") or 0),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_anti_repeat_composition_cues_avoided_count",
                value=float(
                    decision.telemetry.get("anti_repeat_composition_cues_avoided_count") or 0
                ),
                tags=reasoning_tags,
            )
            await self.metrics_recorder.observe(
                "reasoning_anti_repeat_visual_motifs_avoided_count",
                value=float(decision.telemetry.get("anti_repeat_visual_motifs_avoided_count") or 0),
                tags=reasoning_tags,
            )
            if decision.telemetry.get("reasoning_clarification_required"):
                await self.metrics_recorder.increment("reasoning_clarifications", tags=reasoning_tags)
            profile_clarification_decision = decision.telemetry.get("reasoning_profile_clarification_decision")
            if profile_clarification_decision:
                await self.metrics_recorder.increment(
                    "reasoning_profile_clarification_decisions",
                    tags={
                        **reasoning_tags,
                        "profile_clarification_decision": str(profile_clarification_decision),
                    },
                )
            if decision.telemetry.get("reasoning_cta_offered"):
                await self.metrics_recorder.increment("reasoning_visual_cta_offered", tags=reasoning_tags)
            if decision.telemetry.get("reasoning_generation_ready"):
                await self.metrics_recorder.increment("reasoning_generation_ready", tags=reasoning_tags)
            if decision.telemetry.get("reasoning_profile_context_present"):
                await self.metrics_recorder.increment("reasoning_profile_context_present", tags=reasoning_tags)
            cta_decision_reason = decision.telemetry.get("cta_decision_reason")
            if cta_decision_reason:
                await self.metrics_recorder.increment(
                    "reasoning_cta_decisions",
                    tags={**reasoning_tags, "cta_decision_reason": str(cta_decision_reason)},
                )
            if decision.telemetry.get("reasoning_voice_payload_ready"):
                await self.metrics_recorder.increment("reasoning_voice_payload_ready", tags=reasoning_tags)
                await self.metrics_recorder.increment(
                    "reasoning_voice_layer_runs",
                    tags={
                        **reasoning_tags,
                        "voice_response_type": str(
                            decision.telemetry.get("reasoning_voice_response_type") or "unknown"
                        ),
                        "voice_tone_profile": str(
                            decision.telemetry.get("reasoning_voice_tone_profile") or "unknown"
                        ),
                    },
                )
            if decision.telemetry.get("reasoning_voice_historical_used"):
                await self.metrics_recorder.increment(
                    "reasoning_voice_historical_layer_used",
                    tags=reasoning_tags,
                )
            if decision.telemetry.get("reasoning_voice_color_poetics_used"):
                await self.metrics_recorder.increment(
                    "reasoning_voice_color_poetics_layer_used",
                    tags=reasoning_tags,
                )
            if decision.telemetry.get("reasoning_voice_cta_present"):
                await self.metrics_recorder.increment(
                    "reasoning_voice_cta_present",
                    tags={
                        **reasoning_tags,
                        "voice_cta_style": str(
                            decision.telemetry.get("reasoning_voice_cta_style") or "unknown"
                        ),
                    },
                )
            if decision.telemetry.get("reasoning_generation_handoff_ready"):
                await self.metrics_recorder.increment(
                    "reasoning_generation_handoff_ready",
                    tags=reasoning_tags,
                )
            blocked_reason = decision.telemetry.get("reasoning_generation_blocked_reason")
            if blocked_reason:
                await self.metrics_recorder.increment(
                    "reasoning_generation_blocked",
                    tags={**reasoning_tags, "blocked_reason": str(blocked_reason)},
                )

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
        if decision.generation_payload is not None and decision.generation_payload.generation_intent is not None:
            context.generation_intent = decision.generation_payload.generation_intent
            return decision.generation_payload.generation_intent
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
            "can_offer_visualization": context.visualization_offer.can_offer_visualization
            if context.visualization_offer is not None
            else False,
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
        if context.visualization_offer is not None:
            patch["visualization_offer"] = context.visualization_offer.model_dump(mode="json", exclude_none=True)
            patch["cta_text"] = context.visualization_offer.cta_text
            patch["visualization_type"] = context.visualization_offer.visualization_type
        return patch

    def _flow_state_from_generation_status(self, status: str) -> FlowState:
        if status == GenerationStatus.PENDING.value:
            return FlowState.GENERATION_QUEUED
        if status in {GenerationStatus.QUEUED.value, GenerationStatus.RUNNING.value}:
            return FlowState.GENERATION_IN_PROGRESS
        if status == GenerationStatus.COMPLETED.value:
            return FlowState.COMPLETED
        return FlowState.RECOVERABLE_ERROR
