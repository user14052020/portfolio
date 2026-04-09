from pydantic import BaseModel

from app.domain.chat_context import ChatModeContext, CommandContext
from app.domain.chat_modes import ChatMode, FlowState


STARTABLE_FLOW_STATES = {FlowState.IDLE}


class ModeResolution(BaseModel):
    active_mode: ChatMode
    started_new_mode: bool
    continue_existing_flow: bool
    requested_intent: ChatMode | None = None
    command_context: CommandContext | None = None


class ChatModeResolver:
    def resolve(
        self,
        *,
        context: ChatModeContext,
        requested_intent: ChatMode | None,
        command_name: str | None,
        command_step: str | None,
        metadata: dict | None,
    ) -> ModeResolution:
        command_context = CommandContext(
            command_name=command_name,
            command_step=command_step,
            metadata=metadata or {},
        )

        if requested_intent is not None:
            return ModeResolution(
                active_mode=requested_intent,
                started_new_mode=requested_intent != context.active_mode or context.flow_state in STARTABLE_FLOW_STATES,
                continue_existing_flow=requested_intent == context.active_mode and context.flow_state not in STARTABLE_FLOW_STATES,
                requested_intent=requested_intent,
                command_context=command_context,
            )

        if context.flow_state != FlowState.IDLE:
            return ModeResolution(
                active_mode=context.active_mode,
                started_new_mode=False,
                continue_existing_flow=True,
                requested_intent=context.requested_intent,
                command_context=context.command_context or command_context,
            )

        return ModeResolution(
            active_mode=ChatMode.GENERAL_ADVICE,
            started_new_mode=context.active_mode != ChatMode.GENERAL_ADVICE or context.flow_state != FlowState.IDLE,
            continue_existing_flow=False,
            requested_intent=None,
            command_context=command_context,
        )


chat_mode_resolver = ChatModeResolver()
