from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder
from app.domain.chat_context import ChatModeContext
from app.domain.state_machine.occasion_outfit_machine import OccasionOutfitStateMachine


class StartOccasionOutfitUseCase:
    def __init__(self, clarification_builder: ClarificationMessageBuilder) -> None:
        self.clarification_builder = clarification_builder

    def execute(self, *, context: ChatModeContext, locale: str) -> str:
        prompt = self.clarification_builder.occasion_entry_prompt(locale)
        OccasionOutfitStateMachine.enter(context, prompt_text=prompt)
        return prompt
