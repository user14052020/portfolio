from app.application.stylist_chat.results.decision_result import DecisionResult, DecisionType
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState


class PostActionConversationPolicy:
    def apply(
        self,
        *,
        context: ChatModeContext,
        decision: DecisionResult,
    ) -> ChatModeContext:
        if decision.can_offer_visualization:
            context.flow_state = FlowState.READY_FOR_GENERATION
            context.should_auto_generate = False
            return context

        if decision.decision_type == DecisionType.TEXT_ONLY and context.active_mode == ChatMode.GENERAL_ADVICE:
            context.flow_state = FlowState.COMPLETED
            context.should_auto_generate = False
            return context

        if decision.decision_type == DecisionType.CLARIFICATION_REQUIRED:
            context.should_auto_generate = False
            return context

        if decision.requires_generation():
            context.should_auto_generate = False
            return context

        if decision.decision_type in {DecisionType.ERROR_RECOVERABLE, DecisionType.ERROR_HARD}:
            context.should_auto_generate = False
            return context

        return context

