from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState


class GeneralAdviceStateMachine:
    @staticmethod
    def enter(context: ChatModeContext) -> ChatModeContext:
        context.active_mode = ChatMode.GENERAL_ADVICE
        context.flow_state = FlowState.AWAITING_USER_MESSAGE
        context.pending_clarification = None
        context.clarification_kind = None
        context.clarification_attempts = 0
        context.should_auto_generate = False
        return context

    @staticmethod
    def accept_user_message(context: ChatModeContext) -> ChatModeContext:
        context.flow_state = FlowState.READY_FOR_DECISION
        context.pending_clarification = None
        context.clarification_kind = None
        return context

    @staticmethod
    def complete(context: ChatModeContext) -> ChatModeContext:
        context.flow_state = FlowState.COMPLETED
        return context

