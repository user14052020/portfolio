from app.domain.chat_context import AnchorGarment, ChatModeContext
from app.domain.chat_modes import ChatMode, ClarificationKind, FlowState


class GarmentMatchingStateMachine:
    @staticmethod
    def enter(context: ChatModeContext, *, prompt_text: str) -> ChatModeContext:
        context.active_mode = ChatMode.GARMENT_MATCHING
        context.flow_state = FlowState.AWAITING_ANCHOR_GARMENT
        context.should_auto_generate = False
        context.anchor_garment = None
        context.pending_clarification = prompt_text
        context.clarification_kind = ClarificationKind.ANCHOR_GARMENT_DESCRIPTION
        context.clarification_attempts = 0
        return context

    @staticmethod
    def consume_anchor_garment(
        context: ChatModeContext,
        *,
        anchor_garment: AnchorGarment,
        clarification_text: str | None = None,
    ) -> ChatModeContext:
        context.anchor_garment = anchor_garment
        if anchor_garment.is_sufficient_for_generation:
            context.flow_state = FlowState.READY_FOR_DECISION
            context.pending_clarification = None
            context.clarification_kind = None
            return context

        context.flow_state = FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION
        context.pending_clarification = clarification_text
        context.clarification_kind = ClarificationKind.ANCHOR_GARMENT_MISSING_ATTRIBUTES
        context.clarification_attempts += 1
        return context

    @staticmethod
    def mark_ready_for_generation(context: ChatModeContext) -> ChatModeContext:
        context.flow_state = FlowState.READY_FOR_GENERATION
        return context

    @staticmethod
    def mark_generation_queued(context: ChatModeContext, *, job_id: str | None) -> ChatModeContext:
        context.flow_state = FlowState.GENERATION_QUEUED
        context.current_job_id = job_id
        return context

    @staticmethod
    def complete(context: ChatModeContext) -> ChatModeContext:
        context.flow_state = FlowState.COMPLETED
        return context
