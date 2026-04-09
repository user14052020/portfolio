from app.domain.chat_context import ChatModeContext, OccasionContext
from app.domain.chat_modes import ChatMode, ClarificationKind, FlowState


class OccasionOutfitStateMachine:
    @staticmethod
    def enter(context: ChatModeContext, *, prompt_text: str) -> ChatModeContext:
        context.active_mode = ChatMode.OCCASION_OUTFIT
        context.flow_state = FlowState.AWAITING_OCCASION_DETAILS
        context.should_auto_generate = True
        context.pending_clarification = prompt_text
        context.clarification_kind = ClarificationKind.OCCASION_MISSING_MULTIPLE_SLOTS
        context.clarification_attempts = 0
        context.occasion_context = None
        return context

    @staticmethod
    def consume_occasion_context(
        context: ChatModeContext,
        *,
        occasion_context: OccasionContext,
        clarification_kind: ClarificationKind | None,
        clarification_text: str | None,
    ) -> ChatModeContext:
        context.occasion_context = occasion_context
        if occasion_context.is_sufficient_for_generation:
            context.flow_state = FlowState.READY_FOR_DECISION
            context.pending_clarification = None
            context.clarification_kind = None
            return context

        context.flow_state = FlowState.AWAITING_CLARIFICATION
        context.pending_clarification = clarification_text
        context.clarification_kind = clarification_kind
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

