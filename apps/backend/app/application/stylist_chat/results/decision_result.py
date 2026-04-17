from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.chat_context import GenerationIntent
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.product_behavior.entities.visualization_offer import VisualizationOffer


class DecisionType(str, Enum):
    TEXT_ONLY = "text_only"
    CLARIFICATION_REQUIRED = "clarification_required"
    TEXT_AND_GENERATE = "text_and_generate"
    GENERATION_ONLY = "generation_only"
    ERROR_RECOVERABLE = "error_recoverable"
    ERROR_HARD = "error_hard"


class GenerationPayload(BaseModel):
    prompt: str
    image_brief_en: str
    recommendation_text: str
    input_asset_id: int | None = None
    negative_prompt: str | None = None
    visual_preset: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    visual_generation_plan: dict[str, Any] | None = None
    generation_metadata: dict[str, Any] | None = None
    generation_intent: GenerationIntent | None = None


class DecisionResult(BaseModel):
    decision_type: DecisionType
    active_mode: ChatMode
    flow_state: FlowState
    text_reply: str | None = None
    generation_payload: GenerationPayload | None = None
    job_id: str | None = None
    context_patch: dict[str, Any] = Field(default_factory=dict)
    telemetry: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    visualization_offer: VisualizationOffer | None = None
    can_offer_visualization: bool = False
    cta_text: str | None = None
    visualization_type: str | None = None

    def requires_generation(self) -> bool:
        return self.decision_type in {
            DecisionType.TEXT_AND_GENERATE,
            DecisionType.GENERATION_ONLY,
        }

    def apply_visualization_offer(self, offer: VisualizationOffer | None) -> None:
        self.visualization_offer = offer
        self.can_offer_visualization = bool(offer and offer.can_offer_visualization)
        self.cta_text = offer.cta_text if offer is not None else None
        self.visualization_type = offer.visualization_type if offer is not None else None
