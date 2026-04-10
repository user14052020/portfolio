from app.application.stylist_chat.handlers.protocol import ChatModeHandler
from app.domain.chat_modes import ChatMode


class ModeRouter:
    def __init__(self, *, handlers: dict[ChatMode, ChatModeHandler]) -> None:
        self.handlers = handlers

    def route(self, mode: ChatMode) -> ChatModeHandler:
        handler = self.handlers.get(mode)
        if handler is None:
            raise KeyError(f"Handler for mode {mode.value} is not registered")
        return handler
