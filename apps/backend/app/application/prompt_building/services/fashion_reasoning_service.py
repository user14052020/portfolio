from typing import Any

from pydantic import BaseModel, Field

from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.reasoning import (
    KnowledgeContext,
    ProfileContextSnapshot,
    StyleAdviceFacet,
    StyleImageFacet,
    StyleKnowledgeCard,
    StyleRelationFacet,
    StyleSemanticFragmentSummary,
    StyleVisualLanguageFacet,
    UsedStyleReference,
)
from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints


class FashionReasoningInput(BaseModel):
    mode: str
    user_request: str | None = None
    user_message: str | None = None
    recent_conversation_summary: str | None = None
    anchor_garment: dict[str, Any] | None = None
    occasion_context: dict[str, Any] | None = None
    style_direction: dict[str, Any] | None = None
    style_history: list[dict[str, Any]] = Field(default_factory=list)
    used_style_history: list[UsedStyleReference] = Field(default_factory=list)
    diversity_constraints: dict[str, Any] = Field(default_factory=dict)
    structured_diversity_constraints: DiversityConstraints | None = None
    active_slots: dict[str, str] = Field(default_factory=dict)
    knowledge_cards: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_bundle: dict[str, Any] | None = None
    knowledge_context: KnowledgeContext | None = None
    profile_context: dict[str, Any] | None = None
    profile_context_snapshot: ProfileContextSnapshot | None = None
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
    generation_intent: bool = False
    can_generate_now: bool = False
    retrieval_profile: str | None = None
    style_context: list[StyleKnowledgeCard] = Field(default_factory=list)
    style_advice_facets: list[StyleAdviceFacet] = Field(default_factory=list)
    style_image_facets: list[StyleImageFacet] = Field(default_factory=list)
    style_visual_language_facets: list[StyleVisualLanguageFacet] = Field(default_factory=list)
    style_relation_facets: list[StyleRelationFacet] = Field(default_factory=list)
    style_semantic_fragments: list[StyleSemanticFragmentSummary] = Field(default_factory=list)

    def effective_user_request(self) -> str | None:
        return self.user_request or self.user_message


class FashionReasoningService:
    def __init__(self, *, brief_builder) -> None:
        self.brief_builder = brief_builder

    async def build_brief(self, *, reasoning_input: FashionReasoningInput) -> FashionBrief:
        return await self.brief_builder.build(reasoning_input=reasoning_input)
