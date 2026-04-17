from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.routing.enums.routing_mode import ROUTING_MODES, RoutingMode


class RoutingInput(BaseModel):
    user_message: str = ""
    active_mode: RoutingMode | None = None
    flow_state: str | None = None
    pending_slots: list[str] = Field(default_factory=list)
    recent_messages: list[str] = Field(default_factory=list)
    last_ui_action: str | None = None
    profile_hint_present: bool = False
    allowed_modes: list[RoutingMode] = Field(default_factory=lambda: list(ROUTING_MODES))
