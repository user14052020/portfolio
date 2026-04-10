from dataclasses import dataclass

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import ModeResolverPort
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode
from app.services.chat_mode_resolver import ModeResolution


@dataclass(slots=True)
class DispatchResult:
    resolution: ModeResolution
    context: ChatModeContext


class CommandDispatcher:
    def __init__(self, *, mode_resolver: ModeResolverPort) -> None:
        self.mode_resolver = mode_resolver

    def dispatch(self, *, command: ChatCommand, context: ChatModeContext) -> DispatchResult:
        resolution = self.mode_resolver.resolve(
            context=context,
            requested_intent=command.requested_intent,
            command_name=command.command_name,
            command_step=command.command_step,
            metadata=command.metadata,
        )
        if resolution.started_new_mode:
            next_context = context.reset_for_mode(
                mode=resolution.active_mode,
                requested_intent=resolution.requested_intent,
                should_auto_generate=resolution.active_mode != ChatMode.GENERAL_ADVICE,
                command_context=resolution.command_context,
            )
        else:
            next_context = context
            next_context.active_mode = resolution.active_mode
            next_context.requested_intent = resolution.requested_intent
            next_context.command_context = resolution.command_context
            next_context.should_auto_generate = resolution.active_mode != ChatMode.GENERAL_ADVICE

        next_context.remember(role="user", content=command.normalized_message())
        return DispatchResult(resolution=resolution, context=next_context)
