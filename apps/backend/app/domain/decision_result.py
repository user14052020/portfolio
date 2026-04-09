from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.domain.chat_context import GenerationIntent
from app.domain.chat_modes import ChatMode, FlowState


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
    generation_intent: GenerationIntent | None = None


class DecisionResult(BaseModel):
    decision_type: DecisionType
    active_mode: ChatMode
    flow_state: FlowState
    text_reply: str | None = None
    generation_payload: GenerationPayload | None = None
    job_id: str | None = None
    context_patch: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None

    def requires_generation(self) -> bool:
        return self.decision_type in {
            DecisionType.TEXT_AND_GENERATE,
            DecisionType.GENERATION_ONLY,
        }
