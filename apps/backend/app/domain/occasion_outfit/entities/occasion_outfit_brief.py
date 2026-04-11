from pydantic import BaseModel, Field

from app.domain.occasion_outfit.entities.occasion_context import OccasionContext


class OccasionOutfitBrief(BaseModel):
    occasion_context: OccasionContext
    styling_goal: str
    dress_code_logic: list[str] = Field(default_factory=list)
    impression_logic: list[str] = Field(default_factory=list)
    color_logic: list[str] = Field(default_factory=list)
    silhouette_logic: list[str] = Field(default_factory=list)
    garment_recommendations: list[str] = Field(default_factory=list)
    footwear_recommendations: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    outerwear_notes: list[str] = Field(default_factory=list)
    comfort_notes: list[str] = Field(default_factory=list)
    historical_reference: list[str] = Field(default_factory=list)
    tailoring_notes: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    image_prompt_notes: list[str] = Field(default_factory=list)
