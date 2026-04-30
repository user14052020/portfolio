from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.application.stylist_chat.results.decision_result import DecisionResult
from app.domain.chat_context import ChatModeContext
from app.domain.interaction_throttle import ThrottleActionType
from app.models.enums import ChatMessageRole
from app.schemas.common import TimestampedRead
from app.schemas.generation_job import GenerationJobRead
from app.schemas.upload import UploadedAssetRead


class StylistMessageRequest(BaseModel):
    session_id: str
    locale: str = "en"
    message: str | None = None
    asset_id: int | None = None
    uploaded_asset_id: int | None = None
    requested_intent: Literal["general_advice", "garment_matching", "style_exploration", "occasion_outfit"] | None = None
    command_name: str | None = None
    command_step: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    client_message_id: str | None = None
    command_id: str | None = None
    correlation_id: str | None = None
    profile_gender: str | None = None
    body_height_cm: int | None = None
    body_weight_kg: int | None = None
    profile_context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def sync_asset_ids(self) -> "StylistMessageRequest":
        if self.uploaded_asset_id is None and self.asset_id is not None:
            self.uploaded_asset_id = self.asset_id
        if self.asset_id is None and self.uploaded_asset_id is not None:
            self.asset_id = self.uploaded_asset_id
        if self.client_message_id is None:
            raw_value = self.metadata.get("clientMessageId") or self.metadata.get("client_message_id")
            if isinstance(raw_value, str):
                self.client_message_id = raw_value.strip() or None
        if self.command_id is None:
            raw_value = self.metadata.get("commandId") or self.metadata.get("command_id")
            if isinstance(raw_value, str):
                self.command_id = raw_value.strip() or None
        if self.command_id is None:
            self.command_id = self.client_message_id
        if self.correlation_id is None:
            raw_value = self.metadata.get("correlationId") or self.metadata.get("correlation_id")
            if isinstance(raw_value, str):
                self.correlation_id = raw_value.strip() or None
        if self.correlation_id is None:
            self.correlation_id = self.command_id
        return self


class ChatMessageRead(TimestampedRead):
    id: int
    session_id: str
    role: ChatMessageRole
    locale: str
    content: str
    generation_job_id: int | None = None
    generation_job: GenerationJobRead | None = None
    uploaded_asset: UploadedAssetRead | None = None
    payload: dict


class ChatHistoryPageRead(BaseModel):
    items: list[ChatMessageRead]
    has_more: bool
    next_before_message_id: int | None = None


class ChatCooldownStateRead(BaseModel):
    is_allowed: bool
    action_type: ThrottleActionType
    retry_after_seconds: int
    next_allowed_at: datetime | None = None
    cooldown_seconds: int


class ChatRuntimePolicyStateRead(BaseModel):
    cooldown: ChatCooldownStateRead
    remaining_generations: int
    remaining_chat_seconds: int


class StylistMessageResponse(BaseModel):
    session_id: str
    recommendation_text: str
    prompt: str
    assistant_message: ChatMessageRead
    generation_job: GenerationJobRead | None = None
    timestamp: datetime
    decision: DecisionResult
    session_context: ChatModeContext


class StylistVisualizationRequest(BaseModel):
    session_id: str
    locale: str = "en"
    visualization_type: str = "flat_lay_reference"
    message: str | None = None
    asset_id: int | None = None
    uploaded_asset_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    client_message_id: str | None = None
    command_id: str | None = None
    correlation_id: str | None = None
    profile_context: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def sync_asset_ids(self) -> "StylistVisualizationRequest":
        if self.uploaded_asset_id is None and self.asset_id is not None:
            self.uploaded_asset_id = self.asset_id
        if self.asset_id is None and self.uploaded_asset_id is not None:
            self.asset_id = self.uploaded_asset_id
        if self.client_message_id is None:
            raw_value = self.metadata.get("clientMessageId") or self.metadata.get("client_message_id")
            if isinstance(raw_value, str):
                self.client_message_id = raw_value.strip() or None
        if self.command_id is None:
            raw_value = self.metadata.get("commandId") or self.metadata.get("command_id")
            if isinstance(raw_value, str):
                self.command_id = raw_value.strip() or None
        if self.command_id is None:
            self.command_id = self.client_message_id
        if self.correlation_id is None:
            raw_value = self.metadata.get("correlationId") or self.metadata.get("correlation_id")
            if isinstance(raw_value, str):
                self.correlation_id = raw_value.strip() or None
        if self.correlation_id is None:
            self.correlation_id = self.command_id
        return self


class PromptPipelinePreviewRequest(BaseModel):
    mode: Literal["general_advice", "garment_matching", "style_exploration", "occasion_outfit"] = "general_advice"
    user_message: str | None = None
    image_brief_en: str | None = None
    recommendation_text: str | None = None
    asset_id: int | None = None
    profile_context: dict[str, Any] = Field(default_factory=dict)
    style_seed: dict[str, Any] | None = None
    previous_style_directions: list[dict[str, Any]] = Field(default_factory=list)
    anti_repeat_constraints: dict[str, Any] = Field(default_factory=dict)
    occasion_context: dict[str, Any] | None = None
    structured_outfit_brief: dict[str, Any] | None = None
    knowledge_cards: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str | None = None
    message_id: int | None = None
    knowledge_provider_used: str | None = None


class PromptPipelinePreviewResponse(BaseModel):
    fashion_brief: dict[str, Any]
    compiled_prompt: dict[str, Any] | None = None
    generation_payload: dict[str, Any] | None = None
    validation_errors: list[str]


class KnowledgePreviewRequest(BaseModel):
    mode: Literal["general_advice", "garment_matching", "style_exploration", "occasion_outfit"] = "general_advice"
    session_id: str = "debug-session"
    locale: str = "en"
    message: str | None = None
    style_id: str | None = None
    style_ids: list[str | int] = Field(default_factory=list)
    style_name: str | None = None
    style_families: list[str] = Field(default_factory=list)
    eras: list[str] = Field(default_factory=list)
    anchor_garment: dict[str, Any] | None = None
    occasion_context: dict[str, Any] | None = None
    diversity_constraints: dict[str, Any] = Field(default_factory=dict)
    intent: str | None = None
    retrieval_profile: str | None = None
    need_visual_knowledge: bool | None = None
    need_historical_knowledge: bool | None = None
    need_styling_rules: bool | None = None
    need_color_poetics: bool | None = None
    user_request: str | None = None
    limit: int = Field(default=6, ge=1, le=20)
    profile_context: dict[str, Any] = Field(default_factory=dict)


class KnowledgePreviewRuntimeProviderRead(BaseModel):
    code: str
    name: str
    provider_type: str
    priority: int
    runtime_roles: list[str] = Field(default_factory=list)


class KnowledgePreviewRuntimeRead(BaseModel):
    runtime_flags: dict[str, bool]
    provider_priorities: dict[str, int]
    enabled_runtime_providers: list[KnowledgePreviewRuntimeProviderRead] = Field(default_factory=list)


class KnowledgePreviewResponse(BaseModel):
    knowledge_query: dict[str, Any]
    knowledge_context: dict[str, Any]
    knowledge_context_counts: dict[str, int] = Field(default_factory=dict)
    knowledge_observability: dict[str, Any] = Field(default_factory=dict)
    knowledge_runtime: KnowledgePreviewRuntimeRead
    knowledge_bundle: dict[str, Any] | None = None
