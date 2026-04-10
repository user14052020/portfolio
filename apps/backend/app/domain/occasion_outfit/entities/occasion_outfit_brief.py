from pydantic import BaseModel, Field

from app.domain.occasion_outfit.entities.occasion_context import OccasionContext


class OccasionOutfitBrief(BaseModel):
    occasion_context: OccasionContext
    occasion_summary: str
    styling_goal: str
    dressing_rules: list[str] = Field(default_factory=list)
    silhouette_notes: list[str] = Field(default_factory=list)
    palette_direction: list[str] = Field(default_factory=list)
    layering_notes: list[str] = Field(default_factory=list)
    footwear_guidance: list[str] = Field(default_factory=list)
    weather_notes: list[str] = Field(default_factory=list)
    etiquette_notes: list[str] = Field(default_factory=list)
    image_prompt_notes: list[str] = Field(default_factory=list)
