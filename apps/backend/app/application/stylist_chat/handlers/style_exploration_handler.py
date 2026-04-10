from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import StyleHistoryProvider
from app.application.stylist_chat.results.decision_result import DecisionResult
from app.application.stylist_chat.services.diversity_constraints_builder import DiversityConstraintsBuilder
from app.domain.chat_context import ChatModeContext
from app.domain.state_machine.style_exploration_machine import StyleExplorationStateMachine

from .base import BaseChatModeHandler


class StyleExplorationHandler(BaseChatModeHandler):
    def __init__(
        self,
        *,
        style_history_provider: StyleHistoryProvider,
        diversity_constraints_builder: DiversityConstraintsBuilder,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.style_history_provider = style_history_provider
        self.diversity_constraints_builder = diversity_constraints_builder

    async def handle(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        StyleExplorationStateMachine.enter(context)
        previous_style_directions = self.diversity_constraints_builder.to_prompt_items(context.style_history)
        anti_repeat_constraints = self.diversity_constraints_builder.build(context.style_history)
        style_context, style_model = await self.style_history_provider.pick_next(
            session_id=command.session_id,
            style_history=context.style_history,
        )
        StyleExplorationStateMachine.select_style(context, style=style_context)
        if style_model is not None:
            await self.style_history_provider.record_exposure(
                session_id=command.session_id,
                style_direction=style_model,
            )
        StyleExplorationStateMachine.mark_ready_for_generation(context)

        effective_command = command
        if not command.normalized_message():
            effective_command = command.model_copy(
                update={"message": "Новый стиль" if command.locale == "ru" else "Try another style"}
            )

        decision = await self.run_reasoning(
            command=effective_command,
            context=context,
            must_generate=True,
            style_seed=self.style_seed_from_context(style_context),
            previous_style_directions=previous_style_directions,
            occasion_context=None,
            anti_repeat_constraints=anti_repeat_constraints,
            knowledge_mode="style_exploration",
            style_history_used=bool(previous_style_directions),
        )
        context.last_generated_outfit_summary = decision.text_reply
        if decision.generation_payload is not None:
            context.last_generation_prompt = decision.generation_payload.prompt
        return decision
