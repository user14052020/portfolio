from typing import Any

from app.domain.chat_modes import ChatMode
from app.domain.interaction_throttle import (
    THROTTLE_ACTION_MESSAGE,
    THROTTLE_ACTION_TRY_OTHER_STYLE,
    ThrottleActionType,
)


class ChatThrottleActionPolicy:
    def resolve(
        self,
        *,
        source: str | None,
        command_name: str | None,
        command_step: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> ThrottleActionType | None:
        if (
            source == "quick_action"
            and command_name == ChatMode.STYLE_EXPLORATION.value
            and command_step == "start"
        ):
            payload = metadata or {}
            if (
                payload.get("style_selection_strategy") == "random"
                or payload.get("style_exploration_mode") == "random"
                or payload.get("quick_action_id") == "random_style"
            ):
                return THROTTLE_ACTION_TRY_OTHER_STYLE
            preferences = payload.get("style_exploration_preferences")
            return THROTTLE_ACTION_TRY_OTHER_STYLE if isinstance(preferences, dict) else None
        return THROTTLE_ACTION_MESSAGE
