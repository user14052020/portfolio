from dataclasses import dataclass

from app.application.product_behavior.services.conversation_state_policy import ConversationStatePolicy
from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import ConversationRouterPort, ConversationRoutingResult
from app.domain.chat_context import ChatModeContext, CommandContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.routing import RoutingMode
from app.services.chat_mode_resolver import ModeResolution


RESTARTABLE_FLOW_STATES = {
    FlowState.IDLE,
    FlowState.AWAITING_USER_MESSAGE,
    FlowState.AWAITING_ANCHOR_GARMENT,
    FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION,
    FlowState.AWAITING_OCCASION_DETAILS,
    FlowState.AWAITING_OCCASION_CLARIFICATION,
    FlowState.AWAITING_CLARIFICATION,
    FlowState.READY_FOR_DECISION,
    FlowState.READY_FOR_GENERATION,
    FlowState.COMPLETED,
    FlowState.RECOVERABLE_ERROR,
}


@dataclass(slots=True)
class DispatchResult:
    resolution: ModeResolution
    context: ChatModeContext
    routing: ConversationRoutingResult


class CommandDispatcher:
    def __init__(
        self,
        *,
        conversation_router: ConversationRouterPort,
        conversation_state_policy: ConversationStatePolicy,
    ) -> None:
        self.conversation_router = conversation_router
        self.conversation_state_policy = conversation_state_policy

    async def dispatch(self, *, command: ChatCommand, context: ChatModeContext) -> DispatchResult:
        routing = await self.conversation_router.route(
            command=command,
            context=context,
        )
        resolution = self._build_resolution(
            command=command,
            context=context,
            routing=routing,
        )
        next_context = self.conversation_state_policy.apply_dispatch(
            command=command,
            context=context,
            resolution=resolution,
        )
        return DispatchResult(
            resolution=resolution,
            context=next_context,
            routing=routing,
        )

    def _build_resolution(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        routing: ConversationRoutingResult,
    ) -> ModeResolution:
        active_mode = self._coerce_chat_mode(
            routing_mode=routing.decision.mode,
            context=context,
        )
        continue_existing_flow = bool(
            routing.decision.continue_existing_flow
            and context.active_mode == active_mode
        )
        started_new_mode = bool(
            routing.decision.should_reset_to_general
            or active_mode != context.active_mode
            or (not continue_existing_flow and context.flow_state in RESTARTABLE_FLOW_STATES)
        )
        requested_intent = active_mode if active_mode != ChatMode.GENERAL_ADVICE else None
        command_context = CommandContext(
            command_name=command.command_name or self._default_command_name(active_mode=active_mode),
            command_step=command.command_step,
            metadata={
                **dict(command.metadata),
                "routing_decision": routing.decision.model_dump(mode="json"),
                "routing_provider": routing.provider,
                "routing_retrieval_profile": routing.decision.retrieval_profile,
            },
        )
        return ModeResolution(
            active_mode=active_mode,
            started_new_mode=started_new_mode,
            continue_existing_flow=continue_existing_flow,
            requested_intent=requested_intent,
            command_context=command_context,
        )

    def _coerce_chat_mode(
        self,
        *,
        routing_mode: RoutingMode,
        context: ChatModeContext,
    ) -> ChatMode:
        if routing_mode == RoutingMode.CLARIFICATION_ONLY:
            return context.active_mode or ChatMode.GENERAL_ADVICE
        return ChatMode(routing_mode.value)

    def _default_command_name(self, *, active_mode: ChatMode) -> str | None:
        if active_mode == ChatMode.GENERAL_ADVICE:
            return None
        return active_mode.value
