from typing import Any

from pydantic import BaseModel

from app.domain.reasoning import ProfileContext, ProfileContextSnapshot


class ProfileContextInput(BaseModel):
    frontend_hints: dict[str, Any] | None = None
    session_profile: dict[str, Any] | ProfileContextSnapshot | ProfileContext | None = None
    persistent_profile: dict[str, Any] | ProfileContextSnapshot | ProfileContext | None = None
    recent_updates: dict[str, Any] | None = None


class ProfileContextUpdate(BaseModel):
    presentation_profile: str | None = None
    fit_preferences: list[str] | None = None
    silhouette_preferences: list[str] | None = None
    comfort_preferences: list[str] | None = None
    formality_preferences: list[str] | None = None
    color_preferences: list[str] | None = None
    color_avoidances: list[str] | None = None
    preferred_items: list[str] | None = None
    avoided_items: list[str] | None = None
