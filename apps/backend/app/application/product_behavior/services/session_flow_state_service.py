from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.product_behavior.policies.post_generation_reset_rule import PostGenerationResetRule
from app.models.enums import GenerationStatus


class SessionFlowStateService:
    def __init__(self, *, reset_rule: PostGenerationResetRule | None = None) -> None:
        self.reset_rule = reset_rule or PostGenerationResetRule()

    def sync_generation_status(
        self,
        *,
        context: ChatModeContext,
        generation_status: GenerationStatus,
    ) -> ChatModeContext:
        if self.reset_rule.should_reset_to_general(
            context=context,
            generation_status=generation_status,
        ):
            return self._reset_to_general(context)

        context.flow_state = self._flow_state_from_generation_status(generation_status)
        if generation_status in {GenerationStatus.FAILED, GenerationStatus.CANCELLED}:
            context.should_auto_generate = False
        return context

    def _reset_to_general(self, context: ChatModeContext) -> ChatModeContext:
        context.active_mode = ChatMode.GENERAL_ADVICE
        context.requested_intent = None
        context.flow_state = FlowState.IDLE
        context.pending_clarification = None
        context.clarification_kind = None
        context.clarification_attempts = 0
        context.should_auto_generate = False
        context.anchor_garment = None
        context.occasion_context = None
        context.command_context = None
        context.visualization_offer = None
        context.current_job_id = None
        context.last_generation_request_key = None
        context.generation_intent = None
        context.last_decision_type = None
        context.last_generation_prompt = None
        context.last_generated_outfit_summary = None
        context.current_style_id = None
        context.current_style_name = None
        context.last_retrieved_knowledge_refs = []
        return context

    def _flow_state_from_generation_status(self, status: GenerationStatus) -> FlowState:
        if status == GenerationStatus.PENDING:
            return FlowState.GENERATION_QUEUED
        if status in {GenerationStatus.QUEUED, GenerationStatus.RUNNING}:
            return FlowState.GENERATION_IN_PROGRESS
        if status == GenerationStatus.COMPLETED:
            return FlowState.COMPLETED
        return FlowState.RECOVERABLE_ERROR
