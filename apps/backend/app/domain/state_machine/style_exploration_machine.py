from app.domain.chat_context import ChatModeContext, StyleDirectionContext
from app.domain.chat_modes import ChatMode, FlowState


class StyleExplorationStateMachine:
    @staticmethod
    def enter(context: ChatModeContext) -> ChatModeContext:
        context.active_mode = ChatMode.STYLE_EXPLORATION
        context.flow_state = FlowState.READY_FOR_DECISION
        context.should_auto_generate = True
        context.pending_clarification = None
        context.clarification_kind = None
        context.clarification_attempts = 0
        return context

    @staticmethod
    def select_style(context: ChatModeContext, *, style: StyleDirectionContext) -> ChatModeContext:
        context.current_style_id = style.style_id
        context.current_style_name = style.style_name
        context.append_style_history(style)
        context.flow_state = FlowState.READY_FOR_DECISION
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

