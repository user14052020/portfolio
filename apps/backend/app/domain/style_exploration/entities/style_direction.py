from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, model_validator


class StyleDirection(BaseModel):
    style_id: str | None = None
    style_name: str | None = None
    style_family: str | None = None
    palette: list[str] = Field(default_factory=list)
    silhouette_family: str | None = None
    hero_garments: list[str] = Field(default_factory=list)
    footwear: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    styling_mood: list[str] = Field(default_factory=list)
    composition_type: str | None = None
    background_family: str | None = None
    layout_density: str | None = None
    camera_distance: str | None = None
    visual_preset: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_shape(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        if payload.get("silhouette_family") is None and payload.get("silhouette") is not None:
            payload["silhouette_family"] = payload.get("silhouette")
        styling_mood = payload.get("styling_mood")
        if isinstance(styling_mood, str):
            cleaned = styling_mood.strip()
            payload["styling_mood"] = [cleaned] if cleaned else []
        elif styling_mood is None:
            payload["styling_mood"] = []
        return payload

    @property
    def silhouette(self) -> str | None:
        return self.silhouette_family

    @property
    def primary_mood(self) -> str | None:
        return self.styling_mood[0] if self.styling_mood else None

    def key(self) -> str | None:
        return self.style_id or self.style_name
