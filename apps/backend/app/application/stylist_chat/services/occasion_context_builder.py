from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_context import ChatModeContext
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext


class OccasionContextBuilder:
    def build(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        occasion_context: OccasionContext,
    ) -> dict[str, Any]:
        return {
            "locale": command.locale,
            "profile_context": command.profile_context,
            "asset_metadata": command.asset_metadata,
            "session_id": command.session_id,
            "last_generated_outfit_summary": context.last_generated_outfit_summary,
            "last_generation_prompt": context.last_generation_prompt,
            "conversation_history": [
                memory.model_dump(mode="json", exclude_none=True)
                for memory in context.conversation_memory[-4:]
            ],
            "occasion_context": occasion_context.model_dump(exclude_none=True),
        }
