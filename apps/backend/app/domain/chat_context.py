from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.chat_modes import ChatMode, ClarificationKind, FlowState


CURRENT_CHAT_CONTEXT_VERSION = 1
MAX_CONVERSATION_MEMORY = 8
MAX_STYLE_HISTORY = 5


class ConversationMemoryItem(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CommandContext(BaseModel):
    command_name: str | None = None
    command_step: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnchorGarment(BaseModel):
    raw_user_text: str | None = None
    garment_type: str | None = None
    color: str | None = None
    secondary_colors: list[str] = Field(default_factory=list)
    material: str | None = None
    fit: str | None = None
    silhouette: str | None = None
    seasonality: str | None = None
    formality: str | None = None
    gender_context: str | None = None
    confidence: float = 0.0
    is_sufficient_for_generation: bool = False

    def missing_attributes(self) -> list[str]:
        missing: list[str] = []
        if not self.garment_type:
            missing.append("garment_type")
        if not (self.color or self.material or self.fit):
            missing.append("anchor_attributes")
        return missing


class OccasionContext(BaseModel):
    event_type: str | None = None
    location: str | None = None
    time_of_day: str | None = None
    season: str | None = None
    dress_code: str | None = None
    weather_context: str | None = None
    desired_impression: str | None = None
    constraints: list[str] = Field(default_factory=list)
    is_sufficient_for_generation: bool = False

    def missing_core_slots(self) -> list[str]:
        missing: list[str] = []
        if not self.event_type:
            missing.append("event_type")
        if not self.time_of_day:
            missing.append("time_of_day")
        if not self.season:
            missing.append("season")
        if not (self.dress_code or self.desired_impression):
            missing.append("dress_code_or_desired_impression")
        return missing


class StyleDirection(BaseModel):
    style_id: str | None = None
    style_name: str | None = None
    palette: list[str] = Field(default_factory=list)
    silhouette: str | None = None
    hero_garments: list[str] = Field(default_factory=list)
    footwear: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    styling_mood: str | None = None
    composition_type: str | None = None
    background_family: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


StyleDirectionContext = StyleDirection


class GenerationIntent(BaseModel):
    mode: ChatMode
    trigger: str
    reason: str
    must_generate: bool
    job_priority: str = "normal"
    source_message_id: int | None = None


class ChatModeContext(BaseModel):
    version: int = CURRENT_CHAT_CONTEXT_VERSION
    active_mode: ChatMode = ChatMode.GENERAL_ADVICE
    requested_intent: ChatMode | None = None
    flow_state: FlowState = FlowState.IDLE
    pending_clarification: str | None = None
    clarification_kind: ClarificationKind | None = None
    clarification_attempts: int = 0
    should_auto_generate: bool = False
    anchor_garment: AnchorGarment | None = None
    occasion_context: OccasionContext | None = None
    style_history: list[StyleDirection] = Field(default_factory=list)
    last_generation_prompt: str | None = None
    last_generated_outfit_summary: str | None = None
    conversation_memory: list[ConversationMemoryItem] = Field(default_factory=list)
    command_context: CommandContext | None = None
    current_style_id: str | None = None
    current_style_name: str | None = None
    current_job_id: str | None = None
    last_generation_request_key: str | None = None
    last_decision_type: str | None = None
    generation_intent: GenerationIntent | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by_message_id: int | None = None

    def remember(self, *, role: Literal["user", "assistant", "system"], content: str) -> None:
        trimmed = content.strip()
        if not trimmed:
            return
        self.conversation_memory.append(ConversationMemoryItem(role=role, content=trimmed[:400]))
        self.conversation_memory = self.conversation_memory[-MAX_CONVERSATION_MEMORY:]

    def append_style_history(self, style: StyleDirection) -> None:
        style_key = style.style_id or style.style_name
        retained: list[StyleDirection] = []
        for existing in self.style_history:
            existing_key = existing.style_id or existing.style_name
            if existing_key and style_key and existing_key == style_key:
                continue
            retained.append(existing)
        retained.append(style)
        self.style_history = retained[-MAX_STYLE_HISTORY:]

    def touch(self, *, message_id: int | None = None) -> None:
        self.version = max(self.version, CURRENT_CHAT_CONTEXT_VERSION)
        self.updated_at = datetime.now(timezone.utc)
        self.updated_by_message_id = message_id

    def reset_for_mode(
        self,
        *,
        mode: ChatMode,
        requested_intent: ChatMode | None,
        should_auto_generate: bool,
        command_context: CommandContext | None,
    ) -> "ChatModeContext":
        return ChatModeContext(
            version=max(self.version, CURRENT_CHAT_CONTEXT_VERSION),
            active_mode=mode,
            requested_intent=requested_intent,
            flow_state=FlowState.IDLE,
            should_auto_generate=should_auto_generate,
            style_history=[item.model_copy(deep=True) for item in self.style_history],
            last_generated_outfit_summary=self.last_generated_outfit_summary,
            conversation_memory=[item.model_copy(deep=True) for item in self.conversation_memory[-MAX_CONVERSATION_MEMORY:]],
            command_context=command_context,
            updated_at=datetime.now(timezone.utc),
        )
