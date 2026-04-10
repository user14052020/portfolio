from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_context import ChatModeContext
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment


class GarmentMatchingContextBuilder:
    def build(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        garment: AnchorGarment,
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
            "anchor_garment": garment.model_dump(exclude_none=True),
        }
