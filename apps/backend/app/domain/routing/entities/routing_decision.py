from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.routing.enums.reasoning_depth import ReasoningDepth
from app.domain.routing.enums.routing_mode import RoutingMode


class RoutingDecision(BaseModel):
    mode: RoutingMode = RoutingMode.GENERAL_ADVICE
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    needs_clarification: bool = False
    missing_slots: list[str] = Field(default_factory=list)
    generation_intent: bool = False
    continue_existing_flow: bool = False
    should_reset_to_general: bool = False
    reasoning_depth: ReasoningDepth = ReasoningDepth.NORMAL
    retrieval_profile: str | None = None
    notes: str | None = None
    requires_style_retrieval: bool = False
    requires_historical_layer: bool = False
    requires_stylist_guidance: bool = False

    @classmethod
    def safe_default(cls) -> "RoutingDecision":
        return cls(
            mode=RoutingMode.GENERAL_ADVICE,
            confidence=0.0,
            needs_clarification=False,
            missing_slots=[],
            generation_intent=False,
            continue_existing_flow=False,
            should_reset_to_general=False,
            reasoning_depth=ReasoningDepth.LIGHT,
            retrieval_profile=None,
        )
