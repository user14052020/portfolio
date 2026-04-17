from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.product_behavior.policies.conversation_mode_policy import VISUAL_CONFIRMATION_SOURCES
from app.models.enums import GenerationStatus


class PostGenerationResetRule:
    def should_reset_to_general(
        self,
        *,
        context: ChatModeContext,
        generation_status: GenerationStatus,
    ) -> bool:
        if generation_status != GenerationStatus.COMPLETED:
            return False
        if context.pending_clarification:
            return False
        if context.flow_state in {
            FlowState.AWAITING_ANCHOR_GARMENT,
            FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION,
            FlowState.AWAITING_OCCASION_DETAILS,
            FlowState.AWAITING_OCCASION_CLARIFICATION,
            FlowState.AWAITING_CLARIFICATION,
        }:
            return False
        if context.active_mode == ChatMode.STYLE_EXPLORATION:
            return True
        source = None
        if context.command_context is not None:
            raw_source = context.command_context.metadata.get("source")
            if isinstance(raw_source, str):
                source = raw_source.strip() or None
        if source in VISUAL_CONFIRMATION_SOURCES:
            return True
        if context.generation_intent is None:
            return False
        return context.generation_intent.trigger in {
            ChatMode.STYLE_EXPLORATION.value,
            "visualization_cta",
            "explicit_visual_request",
        }
