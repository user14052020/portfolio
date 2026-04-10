from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionResult
from app.domain.chat_context import ChatModeContext
from app.domain.state_machine.general_advice_machine import GeneralAdviceStateMachine

from .base import BaseChatModeHandler


class GeneralAdviceHandler(BaseChatModeHandler):
    async def handle(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        GeneralAdviceStateMachine.enter(context)
        GeneralAdviceStateMachine.accept_user_message(context)
        context.should_auto_generate = self.generation_request_builder.explicitly_requests_generation(
            command.normalized_message()
        )
        decision = await self.run_reasoning(
            command=command,
            context=context,
            must_generate=False,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
            knowledge_mode="general_advice",
            style_history_used=False,
        )
        if decision.requires_generation():
            context.flow_state = decision.flow_state
        else:
            GeneralAdviceStateMachine.complete(context)
            decision.flow_state = context.flow_state
        return decision
