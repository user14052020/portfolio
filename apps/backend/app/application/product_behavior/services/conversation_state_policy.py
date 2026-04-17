from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_context import ChatModeContext
from app.domain.product_behavior.policies.conversation_mode_policy import ConversationModePolicy
from app.services.chat_mode_resolver import ModeResolution


class ConversationStatePolicy:
    def __init__(self, *, mode_policy: ConversationModePolicy | None = None) -> None:
        self.mode_policy = mode_policy or ConversationModePolicy()

    def apply_dispatch(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        resolution: ModeResolution,
    ) -> ChatModeContext:
        should_auto_generate = self.mode_policy.should_allow_generation(
            source=command.source,
            message=command.normalized_message(),
            command_name=command.command_name,
            command_step=command.command_step,
            active_mode=resolution.active_mode,
            context=context,
        )
        if resolution.started_new_mode:
            next_context = context.reset_for_mode(
                mode=resolution.active_mode,
                requested_intent=resolution.requested_intent,
                should_auto_generate=should_auto_generate,
                command_context=resolution.command_context,
            )
        else:
            next_context = context
            next_context.active_mode = resolution.active_mode
            next_context.requested_intent = resolution.requested_intent
            next_context.command_context = resolution.command_context
            next_context.should_auto_generate = should_auto_generate

        next_context.remember(role="user", content=command.normalized_message())
        return next_context
