from app.domain.chat_context import ChatModeContext
from app.domain.state_machine.style_exploration_machine import StyleExplorationStateMachine


class StartStyleExplorationUseCase:
    def execute(self, *, context: ChatModeContext) -> ChatModeContext:
        return StyleExplorationStateMachine.enter(context)
