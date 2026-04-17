from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.routing.enums.routing_mode import RoutingMode


class RoutingMessageExcerpt(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = ""


class ConversationRouterContext(BaseModel):
    active_mode: RoutingMode | None = None
    flow_state: str | None = None
    pending_slots: list[str] = Field(default_factory=list)
    recent_messages: list[RoutingMessageExcerpt] = Field(default_factory=list)
    last_ui_action: str | None = None
    last_generation_completed: bool = False
    last_visual_cta_offered: bool = False
    profile_context_present: bool = False
