from dataclasses import dataclass

from app.application.stylist_chat.contracts.command import ChatCommand
from app.models import UploadedAsset
from app.models.chat_message import ChatMessage


@dataclass(slots=True)
class OrchestrationRequest:
    command: ChatCommand
    asset: UploadedAsset | None
    recent_messages: list[ChatMessage]
