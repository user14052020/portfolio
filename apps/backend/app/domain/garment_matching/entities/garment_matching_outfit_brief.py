from pydantic import BaseModel, Field

from .anchor_garment import AnchorGarment


class GarmentMatchingOutfitBrief(BaseModel):
    anchor_garment: AnchorGarment
    styling_goal: str
    harmony_rules: list[str] = Field(default_factory=list)
    color_logic: list[str] = Field(default_factory=list)
    silhouette_balance: list[str] = Field(default_factory=list)
    complementary_garments: list[str] = Field(default_factory=list)
    footwear_options: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    historical_reference: list[str] = Field(default_factory=list)
    tailoring_notes: list[str] = Field(default_factory=list)
    image_prompt_notes: list[str] = Field(default_factory=list)
