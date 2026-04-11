from app.application.stylist_chat.services.style_history_service import StyleHistoryService
from app.domain.chat_context import ChatModeContext
from app.domain.style_exploration.entities.style_direction import StyleDirection


class PersistStyleDirectionUseCase:
    def __init__(self, *, style_history_service: StyleHistoryService) -> None:
        self.style_history_service = style_history_service

    def execute(self, *, context: ChatModeContext, style_direction: StyleDirection) -> ChatModeContext:
        context.style_history = self.style_history_service.remember(
            history=context.style_history,
            style_direction=style_direction,
        )
        context.current_style_id = style_direction.style_id
        context.current_style_name = style_direction.style_name
        return context
