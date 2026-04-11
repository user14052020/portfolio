from typing import Any

from pydantic import BaseModel, Field

from app.domain.prompt_building.entities.fashion_brief import FashionBrief


class FashionReasoningInput(BaseModel):
    mode: str
    user_message: str | None = None
    anchor_garment: dict[str, Any] | None = None
    occasion_context: dict[str, Any] | None = None
    style_direction: dict[str, Any] | None = None
    style_history: list[dict[str, Any]] = Field(default_factory=list)
    diversity_constraints: dict[str, Any] = Field(default_factory=dict)
    knowledge_cards: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_bundle: dict[str, Any] | None = None
    profile_context: dict[str, Any] | None = None
    visual_preset_candidates: list[str] = Field(default_factory=list)
    structured_outfit_brief: dict[str, Any] | None = None
    recommendation_text: str | None = None
    image_brief_en: str | None = None
    style_seed: dict[str, Any] | None = None
    previous_style_directions: list[dict[str, Any]] = Field(default_factory=list)
    anti_repeat_constraints: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    message_id: int | None = None
    knowledge_provider_used: str | None = None


class FashionReasoningService:
    def __init__(self, *, brief_builder) -> None:
        self.brief_builder = brief_builder

    async def build_brief(self, *, reasoning_input: FashionReasoningInput) -> FashionBrief:
        return await self.brief_builder.build(reasoning_input=reasoning_input)
