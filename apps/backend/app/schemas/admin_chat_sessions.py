from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.generation_job import GenerationJobRead
from app.schemas.stylist import ChatMessageRead


class AdminChatSessionSummary(BaseModel):
    id: int
    session_id: str
    started_at: datetime
    last_message_at: datetime | None = None
    message_count: int
    locale: str | None = None
    client_ip: str | None = None
    client_user_agent: str | None = None
    client_user_agent_short: str | None = None
    last_active_mode: str | None = None
    last_decision_type: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AdminChatSessionsPage(BaseModel):
    items: list[AdminChatSessionSummary]
    total: int
    offset: int
    limit: int


class AdminChatSessionStateSnapshot(BaseModel):
    id: int
    session_id: str
    active_intent: str | None = None
    state_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AdminChatSessionDetails(BaseModel):
    session: AdminChatSessionSummary
    messages: list[ChatMessageRead]
    generation_jobs: list[GenerationJobRead]
    state: AdminChatSessionStateSnapshot | None = None
